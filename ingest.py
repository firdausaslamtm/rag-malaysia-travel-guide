from langchain_community.document_loaders import PyPDFLoader, DirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings
from langchain_community.vectorstores import Chroma

DATA_PATH = "data/docs"
CHROMA_PATH = "data/chroma"

def ingest():
    print(f"Loading PDFs from {DATA_PATH}...")
    loader = DirectoryLoader(DATA_PATH, glob="*.pdf", loader_cls=PyPDFLoader)
    docs = loader.load()

    if not docs:
        print("No PDFs found in data/docs")
        return

    print(f"Loaded {len(docs)} pages")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200
    )
    chunks = splitter.split_documents(docs)
    print(f"Split into {len(chunks)} chunks")

    embeddings = OllamaEmbeddings(model="nomic-embed-text")

    # Delete old DB if exists
    import shutil, os
    if os.path.exists(CHROMA_PATH):
        shutil.rmtree(CHROMA_PATH)

    vectordb = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=CHROMA_PATH
    )
    print(f"Vector store saved to {CHROMA_PATH}")

if __name__ == "__main__":
    ingest()