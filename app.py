import argparse
from dotenv import load_dotenv
load_dotenv()

def ingest(source_dir):
    print(f"[INGEST] Would load public travel PDFs from {source_dir}")
    print("TODO: Parse PDFs, chunk, embed, store in Chroma")

def query(question):
    print(f"[QUERY] {question}")
    print("TODO: Retrieve top-k chunks, call LLM, return answer with sources")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ingest", help="Path to public docs")
    parser.add_argument("--query", help="Question to ask")
    args = parser.parse_args()
    if args.ingest:
        ingest(args.ingest)
    elif args.query:
        query(args.query)
    else:
        print("Use --ingest data/ or --query 'Best time to visit Langkawi?'")
