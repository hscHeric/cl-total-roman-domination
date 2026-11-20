# cl-total-roman-domination

Estudo experimental e implementações de métodos exatos e metaheurísticos (incluindo BRKGA) para o **Total Roman Domination Problem (TRDP)** sobre instâncias reais e sintéticas.

---

## Início rápido: como baixar o repositório e gerar o dataset

### 1. Baixar o repositório

Clone o repositório já trazendo o submódulo [`external/graph-instances`](external/graph-instances):

```bash
# Via SSH (recomendado)
git clone --recurse-submodules git@github.com:hscHeric/cl-total-roman-domination.git
cd cl-total-roman-domination
```

Ou via HTTPS:

```bash
git clone --recurse-submodules https://github.com/hscHeric/cl-total-roman-domination.git
cd cl-total-roman-domination
```

Se você já clonou sem `--recurse-submodules`, inicialize o submódulo com:

```bash
git submodule update --init --recursive
```

---

### 2. Preparar o ambiente (com `mise` ou sem `mise`)

Você pode gerenciar as ferramentas do projeto automaticamente com **`mise`** (recomendado) ou instalá-las manualmente no sistema.

#### Opção A — Com `mise` (recomendado)

O arquivo [`mise.toml`](mise.toml) instala e isola automaticamente `cmake`, `ninja`, `python`, `uv`, `pipx` e `conan` (note que `pipx` e `uv` existem na configuração **apenas para instalar o `conan`** de forma isolada e criar o ambiente virtual):

```bash
mise trust
mise install
```

#### Opção B — Sem `mise` (instalação manual)

Se preferir não usar `mise`, garanta as seguintes ferramentas instaladas no seu sistema:

- **Build C++**: `git`, compilador C++ (GCC ou Clang), `cmake` e `ninja`;
- **Gerenciador de pacotes C++ (`conan`)**: o **`pipx` serve apenas para instalar o `conan`** de forma isolada sem poluir o Python do sistema:
  ```bash
  pipx install conan
  ```
  *(Se você já tiver o `conan` instalado por outro meio — ex.: `uv tool install conan` ou via gerenciador do sistema — não precisa do `pipx`.)*
- **Python (3.12 a 3.14 recomendado)** para os scripts do projeto e para o submódulo `external/graph-instances` (que depende de `numpy`, `scipy`, `scikit-learn` e `networkx`).

Em seguida, crie o ambiente virtual do submódulo `external/graph-instances` e instale as dependências dele:

```bash
cd external/graph-instances
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
deactivate
cd ../..
```

*(Opcional)* Crie também um ambiente virtual na raiz do projeto caso vá instalar dependências dos scripts em `scripts/` ou do solver exato:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

---

### 3. Gerar ou reproduzir o dataset

O script [`scripts/instances/reproduce_dataset.py`](scripts/instances/reproduce_dataset.py) executa o pipeline completo (baixa/converte as 4 bases reais, gera as 4 bases sintéticas, filtra vértices isolados, seleciona 30 instâncias representativas por base, copia os 240 arquivos `.col` para `dataset/processed/<base>/instances/` e valida os hashes **SHA-256**).

No modo automático:
- Se `dataset/processed/<base>/metadata.json` **já existir** (padrão ao clonar o repositório) → **reproduz exatamente** os 240 grafos usando os parâmetros e seeds versionados.
- Se `dataset/processed/<base>/metadata.json` **não existir** → **gera um novo dataset do zero** com novas seeds aleatórias e grava os novos `metadata.json` e `selection.csv`.

#### Com `mise`

```bash
# Modo automático (task única: reproduz se houver metadata.json, ou gera do zero se não houver)
mise run dataset

# Forçar reprodução exata a partir dos metadata.json (mesmas seeds e SHA-256)
mise run dataset:reproduce

# Forçar geração de um NOVO dataset do zero (novas seeds aleatórias nas sintéticas;
# atualiza instances/*.col, metadata.json e selection.csv em dataset/processed/)
mise run dataset:generate

# Atalhos parciais e verificação
mise run dataset:reproduce:synthetic   # reproduzir apenas as 4 bases sintéticas
mise run dataset:reproduce:real        # reproduzir apenas as 4 bases reais
mise run dataset:verify                # apenas verificar a integridade SHA-256 dos .col
```

#### Sem `mise` (chamando o Python diretamente)

Os mesmos comandos funcionam diretamente com `python3`, sem precisar do `mise` (basta ter criado o `.venv` de `external/graph-instances` no passo 2):

```bash
# Modo automático (reproduz se houver metadata.json, ou gera do zero se não houver)
python3 scripts/instances/reproduce_dataset.py --auto

# Forçar reprodução exata a partir dos metadata.json (mesmas seeds e SHA-256)
python3 scripts/instances/reproduce_dataset.py

# Forçar geração de um NOVO dataset do zero (novas seeds aleatórias nas sintéticas;
# atualiza instances/*.col, metadata.json e selection.csv em dataset/processed/)
python3 scripts/instances/reproduce_dataset.py --fresh

# Atalhos parciais e verificação
python3 scripts/instances/reproduce_dataset.py --synthetic-only   # apenas as 4 bases sintéticas
python3 scripts/instances/reproduce_dataset.py --real-only        # apenas as 4 bases reais
python3 scripts/instances/reproduce_dataset.py --verify-only      # apenas verificar SHA-256
```

#### Opções úteis (com ou sem `mise`)

Com `mise`, passe as flags após `--`; sem `mise`, passe diretamente ao `reproduce_dataset.py`:

```bash
# Pré-visualizar todos os comandos sem executar nada
mise run dataset -- --dry-run
python3 scripts/instances/reproduce_dataset.py --auto --dry-run

# Processar apenas bases específicas (ex.: cubic e erdos_renyi)
mise run dataset -- --datasets cubic erdos_renyi
python3 scripts/instances/reproduce_dataset.py --auto --datasets cubic erdos_renyi

# Reaproveitar downloads já presentes em external/graph-instances/datasets/<base>/raw/
mise run dataset:reproduce:real -- --skip-download
python3 scripts/instances/reproduce_dataset.py --real-only --skip-download
```

---

## Estrutura do repositório

```text
.
├── dataset/
│   └── processed/
│       └── <base>/
│           ├── instances/     # Arquivos .col (ignorados pelo Git; gerados via script/task)
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
│   ├── instances/             # Reprodução, geração e verificação SHA-256 do dataset
│   └── tuning/                # Scripts de calibração de hiperparâmetros
├── src/
│   ├── common/                # Parser DIMACS .col, CLI, RNG e utilitários compartilhados
│   ├── problem/               # Modelo TRDP, validador de factibilidade e busca local
│   └── methods/
│       ├── exact/             # Formulação/solver exato (MILP)
│       ├── brkga/             # Método principal (BRKGA)
│       └── secondary/         # Método secundário de comparação
├── tests/                     # Testes unitários e de pipeline
└── mise.toml                  # Versões fixadas de CMake, Conan, Ninja, Python, uv/pipx e tasks
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

### Alternativas para obter ou distribuir o dataset

#### Empacotar / restaurar via arquivo compactado (ex.: GitHub Releases ou Zenodo)

Para distribuir os 240 grafos prontos (sem precisar rebaixar/reconverter o SNAP), basta compactar em um único arquivo (~350–400 MB, aceito gratuitamente em **GitHub Releases** até 2 GB ou no **Zenodo**):

```bash
# Empacotar
tar -I 'zstd -19' -cf dataset-processed-v1.tar.zst dataset/processed/

# Restaurar na raiz do projeto e validar hashes SHA-256
tar -I zstd -xf dataset-processed-v1.tar.zst
python3 scripts/instances/reproduce_dataset.py --verify-only   # ou: mise run dataset:verify
```

#### Execução manual passo a passo diretamente no submódulo

```bash
# 1. Ativar o ambiente virtual do submódulo (criado no passo 2)
cd external/graph-instances
source .venv/bin/activate

# 2. Baixar e converter as 4 bases reais (removendo vértices isolados)
python graph_instances.py download harwell-boeing
python graph_instances.py download dimacs
python graph_instances.py download bhoslib
python graph_instances.py download snap
python graph_instances.py convert all --remove-isolated

# 3. Gerar as 4 bases sintéticas com as seeds exatas registradas em metadata.json
#    (remova --seed <...> caso queira gerar novas instâncias com seeds aleatórias)
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

deactivate
cd ../..
python3 scripts/instances/reproduce_dataset.py --verify-only
```
