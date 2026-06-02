import argparse
from ingest import ingest
from query import query

def main():
    parser = argparse.ArgumentParser(description="RAG Malaysia Travel Guide with Ollama")
    parser.add_argument("--ingest", action="store_true", help="Ingest PDFs from data/docs")
    parser.add_argument("--query", type=str, help="Ask a question")
    args = parser.parse_args()

    if args.ingest:
        print("[INGEST] Building vector store...")
        ingest()
    elif args.query:
        print(f"[QUERY] {args.query}")
        query(args.query)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()