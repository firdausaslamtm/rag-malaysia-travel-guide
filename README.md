# RAG Malaysia Travel Guide

A fully local Retrieval-Augmented Generation chatbot for Malaysia travel information. Built with LangChain, Chroma, and Ollama.

100% offline. No API keys. No cloud calls. Perfect for portfolio demos.

## What it does

1. Loads public PDFs from `data/docs/`
2. Splits into chunks and embeds with Ollama `nomic-embed-text`
3. Stores vectors in Chroma
4. Answers questions using Ollama `llama3.2:3b` with retrieved context
5. Returns answer + source files

## Tech Stack

- **LangChain** - orchestration
- **langchain-ollama** - local embeddings + LLM
- **langchain-chroma** - vector store
- **Ollama** - `nomic-embed-text` + `llama3.2:3b`
- **PyPDF** - PDF loading

## Prerequisites

### 1. Install Ollama

Ollama is NOT a Python package. Install it separately.

**macOS:**
```bash
brew install ollama
```

**Linux:**
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

**Windows:**
Download from https://ollama.com/download and install.

Start the server:
```bash
ollama serve
```
Keep this terminal open.

Pull models:
```bash
ollama pull nomic-embed-text
ollama pull llama3.2:3b
```

Verify:
```bash
ollama list
```
You should see:
```
nomic-embed-text:latest
llama3.2:3b
```

### 2. Python 3.10+

## Installation

```bash
# Clone
git clone <your-repo-url>
cd rag-malaysia-travel-guide

# Create venv
python -m venv .venv
source .venv/bin/activate  # Windows: .\.venv\Scripts\activate

# Install Python deps
pip install -r requirements.txt
```

`requirements.txt`:
```
langchain>=0.2.16
langchain-community>=0.2.16
langchain-text-splitters>=0.2.0
langchain-ollama>=0.1.0
langchain-chroma>=0.1.0
chromadb>=0.5.5
pypdf>=4.2.0
python-dotenv>=1.0.1
```

## Project Structure

```
rag-malaysia-travel-guide/
├── data/
│   ├── docs/
│   │   └── malaysia_travel_guide.pdf   # Add your PDFs here
│   └── chroma/                         # Auto-created after ingest
├── ingest.py                           # Build vector store
├── query.py                            # Query CLI
├── app.py                              # Unified CLI
├── requirements.txt
└── README.md
```

## Quick Start

### Step 1: Add documents
Put PDFs into `data/docs/`:
```bash
ls data/docs/
# malaysia_travel_guide.pdf
```

### Step 2: Ingest
```bash
python app.py --ingest
```

Expected output:
```
[INGEST] Building vector store...
Loading PDFs from data/docs...
Loaded 212 pages
Split into 459 chunks
Vector store saved to data/chroma
```

### Step 3: Query
```bash
python app.py --query "Best time to visit Langkawi?"
```

Sample output:
```
[QUERY] Best time to visit Langkawi?

=== Answer ===

The best time to visit Langkawi is between December and April during the dry season. The weather is sunny with minimal rainfall, ideal for beach activities and island hopping.

=== Sources ===
- malaysia_travel_guide.pdf
```

More examples:
```bash
python app.py --query "What food to try in Penang?"
python app.py --query "Top attractions in Kuala Lumpur?"
python app.py --query "Is Malaysia safe for solo travelers?"
```

Direct scripts:
```bash
python ingest.py
python query.py "What's interesting in Kuala Lumpur?"
```

## Example Session

```bash
$ ollama serve
# in new terminal
$ ollama pull nomic-embed-text
$ ollama pull llama3.2:3b

$ source .venv/bin/activate
$ pip install -r requirements.txt

$ python app.py --ingest
[INGEST] Building vector store...
Loading PDFs from data/docs...
Loaded 212 pages
Split into 459 chunks
Vector store saved to data/chroma

$ python app.py --query "Top attractions in Kuala Lumpur?"

[QUERY] Top attractions in Kuala Lumpur?

=== Answer ===

According to the context, the top attractions in Kuala Lumpur are:

1. Gamuda Cove
2. Discovery Park (a 23-acre adventure park)
3. Paya Indah Discovery Wetlands

These attractions can be found on the following websites:
- www.mpks.gov.my
- gamudaland.com.my/gamudacove/splashmania
- www.selangor.travel
```

## Development Workflow

Add new PDF:
```bash
cp ~/Downloads/new_guide.pdf data/docs/
rm -rf data/chroma
python app.py --ingest
```

Test retrieval quality:
```bash
python app.py --query "your test question"
```

## Troubleshooting

**Error: model 'nomic-embed-text' not found**
```bash
ollama pull nomic-embed-text
```

**Error: model 'llama3.2:3b' not found**
```bash
ollama pull llama3.2:3b
```

**Error: Connection refused**
Ollama server is not running. Start it:
```bash
ollama serve
```

**No results found**
- Check PDF is in `data/docs/`
- Re-ingest: `rm -rf data/chroma && python app.py --ingest`
- Try broader query

**Slow ingestion**
First run is slow because Ollama generates embeddings for all chunks. Subsequent queries are fast.

**zsh: 0.2.0 not found**
When installing with version specifiers, use quotes:
```bash
pip install "langchain-core>=0.2.0"
```

## Configuration

Change models in `query.py` and `ingest.py`:

Embeddings:
```python
embeddings = OllamaEmbeddings(model="nomic-embed-text")
```

LLM:
```python
llm = OllamaLLM(model="llama3.2:3b", temperature=0.3)
```

Try alternatives:
- `llama3:latest` - bigger, slower, smarter
- `phi3:latest` - smaller, faster

Chunk settings in `ingest.py`:
```python
splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200
)
```