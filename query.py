from langchain_ollama import OllamaEmbeddings, OllamaLLM
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate
import os

CHROMA_PATH = "data/chroma"

PROMPT_TEMPLATE = """
Answer the question based only on the following context:

{context}

---
Question: {question}

If the context does not contain the answer, say you don't know.
Provide sources at the end.
"""

def query(question: str):
    embeddings = OllamaEmbeddings(model="nomic-embed-text")
    vectordb = Chroma(persist_directory=CHROMA_PATH, embedding_function=embeddings)

    results = vectordb.similarity_search_with_relevance_scores(question, k=5)

    if len(results) == 0:
        print("No results found")
        return

    context_text = "\n\n---\n\n".join([doc.page_content for doc, _ in results])

    prompt = ChatPromptTemplate.from_template(PROMPT_TEMPLATE).format(
        context=context_text,
        question=question
    )

    llm = OllamaLLM(model="llama3.2:3b", temperature=0.3)
    response = llm.invoke(prompt)

    sources = [os.path.basename(doc.metadata.get("source", "")) for doc, _ in results]

    print("\n=== Answer ===\n")
    print(response)
    print("\n=== Sources ===")
    for s in sorted(set(sources)):
        print("-", s)

if __name__ == "__main__":
    import sys
    q = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Best time to visit Langkawi?"
    query(q)