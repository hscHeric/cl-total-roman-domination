# cl-total-roman-domination

Estudo experimental e implementações de métodos exatos e metaheurísticos (incluindo BRKGA) para o **Total Roman Domination Problem (TRDP)** sobre instâncias reais e sintéticas.

---

## Estrutura do repositório

```text
.
├── dataset/
│   └── processed/
│       └── <base>/
│           ├── instances/     # Arquivos .col (ignorados pelo Git; veja seção Dataset)
│           ├── metadata.json  # Proveniência, seeds, parâmetros e hashes SHA-256
│           └── selection.csv  # 16 features estruturais, clusters K-Means e PCA 2D
├── docs/                      # Notas técnicas e documentação do projeto
├── experiments/
│   ├── configs/               # Configurações de execução
│   ├── suites/                # Definições de suites de instâncias
│   └── tuning/                # Configurações de calibração (BRKGA e método secundário)
├── external/
│   └── graph-instances/       # Submódulo gerador/conversor/seletor de grafos
├── results/                   # Resultados brutos e agregados dos experimentos
├── scripts/
│   ├── analysis/              # Análise estatística, tabelas e gráficos
│   ├── instances/             # Utilitários de organização/verificação de instâncias
│   └── tuning/                # Scripts de calibração de hiperparâmetros
├── src/
│   ├── common/                # Parser DIMACS .col, CLI, RNG e utilitários compartilhados
│   ├── problem/               # Modelo TRDP, validador de factibilidade e busca local
│   └── methods/
│       ├── exact/             # Formulação/solver exato (MILP)
│       ├── brkga/             # Método principal (BRKGA)
│       └── secondary/         # Método secundário de comparação
├── tests/                     # Testes unitários e de pipeline
└── mise.toml                  # Versões fixadas de CMake, Conan, Ninja e Python
```

---

## Ambiente e pré-requisitos

As ferramentas de build e Python são gerenciadas via [`mise`](https://mise.jdx.dev/) conforme [`mise.toml`](mise.toml) (`cmake`, `conan`, `ninja`, `python`).

Ao clonar o repositório, inicialize também o submódulo `external/graph-instances`:

```bash
git clone --recurse-submodules git@github.com:hscHeric/cl-total-roman-domination.git
cd cl-total-roman-domination
```

Se já clonou sem `--recurse-submodules`:

```bash
git submodule update --init --recursive
```

---

## Dataset (`dataset/processed/`)

O benchmark é composto por **240 grafos simples, não-direcionados e sem vértices isolados** no formato DIMACS `.col`, divididos igualmente em **8 famílias** (**30 instâncias representativas por base** selecionadas via K-Means sobre 16 features estruturais com transformação `log1p` e padronização `StandardScaler`, usando `--seed 42`):

| Base | Tipo | Pool Elegível | Pool Clusterizado | Selecionados | `n` Único | `n` Mín | `n` Máx | Silhouette |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `harwell_boeing` | Real (NIST Matrix Market) | 133 | 133 | 30 | 30 | 62 | 44.609 | `0.3176` |
| `dimacs` | Benchmark clássico | 78 | 78 | 30 | 15 | 28 | 4.000 | `0.4109` |
| `bhoslib` | Benchmark difícil | 36 | 36 | 30 | 8 | 450 | 4.000 | `0.0964` |
| `snap` | Real (redes grandes) | 1.010 | 85\* | 30 | 30 | 8 | 3.774.768 | `0.3344` |
| `cubic` | Sintético (3-regular) | 106 | 106 | 30 | 30 | 100 | 9.312 | `0.3919` |
| `erdos_renyi` | Sintético ($G(n,p)$, $\bar{d}=12$) | 102 | 102 | 30 | 30 | 100 | 5.490 | `0.1630` |
| `barabasi_albert` | Sintético ($m=4$) | 103 | 103 | 30 | 30 | 100 | 8.910 | `0.2481` |
| `watts_strogatz` | Sintético ($k=6, p=0.15$) | 98 | 98 | 30 | 30 | 100 | 6.265 | `0.2008` |

\* No `snap`, séries temporais repetitivas (`as-733`, `as-caida`, `oregon1`, `oregon2`, `comm-f2f-resistance`) são limitadas a no máximo 2 snapshots representativos cada (`--max-per-series 2`) antes do K-Means global.

### Por que os arquivos `.col` não são versionados no Git?

A pasta `dataset/processed/` completa soma **~1,8 GB** e contém 4 grafos do SNAP acima do limite rígido de **100 MB por arquivo** do GitHub (`as-skitter.col`, `cit-Patents.col`, `gplus_combined.col` e `soc-pokec-relationships.col`), além de exceder a cota gratuita de 1 GB do Git LFS.

Por isso, o `.gitignore` ignora apenas `dataset/processed/*/instances/*.col`, enquanto **toda a proveniência e verificabilidade permanecem versionadas no Git**:
- `dataset/processed/<base>/metadata.json`: parâmetros, seeds exatas de geração/seleção, estatísticas do K-Means/PCA e **hash SHA-256** de cada um dos 240 arquivos `.col`.
- `dataset/processed/<base>/selection.csv`: tabela completa com as 16 features, atribuição de clusters e projeção PCA 2D.
- `external/graph-instances`: submódulo fixado no commit exato usado na geração e seleção.

---

### Como reproduzir exatamente os 240 arquivos `.col`

#### Opção A — Automática via `mise` (recomendada)

O script [`scripts/instances/reproduce_dataset.py`](scripts/instances/reproduce_dataset.py) lê **automaticamente todos os parâmetros, seeds e configurações de seleção diretamente dos arquivos `dataset/processed/<base>/metadata.json`**, executa o pipeline no submódulo `external/graph-instances`, copia os 30 `.col` selecionados de cada base para `dataset/processed/<base>/instances/` e valida todos os hashes **SHA-256** ao final:

```bash
# Reproduzir todas as 8 bases (download/geração, conversão, filtro, seleção, cópia e verificação SHA-256)
mise run dataset:reproduce

# Reproduzir apenas as 4 bases sintéticas (rápido, sem downloads)
mise run dataset:reproduce:synthetic

# Reproduzir apenas as 4 bases reais (Harwell-Boeing, DIMACS, BHOSLIB, SNAP)
mise run dataset:reproduce:real

# Apenas verificar a integridade SHA-256 dos 240 .col já presentes em dataset/processed/
mise run dataset:verify
```

Também é possível passar opções extras ao script via `--` (por exemplo, pré-visualizar os comandos ou reproduzir apenas bases específicas):

```bash
# Pré-visualizar todos os comandos sem executar nada
mise run dataset:reproduce -- --dry-run

# Reproduzir apenas bases específicas (ex.: cubic e erdos_renyi)
mise run dataset:reproduce -- --datasets cubic erdos_renyi

# Reaproveitar downloads já presentes em external/graph-instances/datasets/<base>/raw/
mise run dataset:reproduce:real -- --skip-download
```

#### Opção B — Empacotar / restaurar via arquivo compactado (ex.: GitHub Releases ou Zenodo)

Para distribuir os 240 grafos prontos (sem precisar rebaixar/reconverter o SNAP), basta compactar em um único arquivo (~350–400 MB, aceito gratuitamente em **GitHub Releases** até 2 GB ou no **Zenodo**):

```bash
# Empacotar
tar -I 'zstd -19' -cf dataset-processed-v1.tar.zst dataset/processed/

# Restaurar na raiz do projeto e validar hashes SHA-256
tar -I zstd -xf dataset-processed-v1.tar.zst
mise run dataset:verify
```

#### Opção C — Execução manual passo a passo (sem `mise`)

```bash
# 1. Preparar o ambiente do submódulo
cd external/graph-instances
source .venv/bin/activate
pip install -r requirements.txt

# 2. Baixar e converter as 4 bases reais (removendo vértices isolados)
python graph_instances.py download harwell-boeing
python graph_instances.py download dimacs
python graph_instances.py download bhoslib
python graph_instances.py download snap
python graph_instances.py convert all --remove-isolated

# 3. Gerar as 4 bases sintéticas com as seeds exatas registradas em metadata.json
python graph_instances.py generate cubic           --doubling 100 1.045 106 --count 1 --seed 1589853731 --remove-isolated
python graph_instances.py generate erdos-renyi     --doubling 100 1.045 103 --avg-degree 12 --count 1 --seed 232044735 --remove-isolated
python graph_instances.py generate barabasi-albert --doubling 100 1.045 103 --m 4 --count 1 --seed 1715692963 --remove-isolated
python graph_instances.py generate watts-strogatz  --doubling 100 1.045 98  --k 6 --p-rewire 0.15 --count 1 --seed 1845657283 --remove-isolated

# 4. Garantir ausência de vértices isolados e selecionar os 30 representantes de cada base
python graph_instances.py filter all --remove-isolated
for ds in harwell-boeing dimacs bhoslib snap cubic erdos-renyi barabasi-albert watts-strogatz; do
  python graph_instances.py select "$ds" --count 30 --seed 42
done

# 5. Copiar os .col selecionados para dataset/processed/ e validar SHA-256
for ds in harwell_boeing dimacs bhoslib snap cubic erdos_renyi barabasi_albert watts_strogatz; do
  mkdir -p "../../dataset/processed/$ds/instances"
  cp "datasets/$ds/selected/"*.col "../../dataset/processed/$ds/instances/"
done

cd ../..
python3 scripts/instances/reproduce_dataset.py --verify-only
```
