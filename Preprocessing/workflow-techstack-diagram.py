"""
    This script uses Graphviz to draw a flowchart of the tech stack for an
    AI Wrapper project with Angular frontend + Flask backend + two LLMs.

    Explanation of key parts:
    - We import `Digraph` from Graphviz to create a directed graph.
    - The graph is given attributes such as `rankdir=LR` to lay out nodes left-to-right.
    - We group related components into clusters (Client, Backend API, Model Services, Data Layer).
    - Each cluster contains labeled nodes representing services, components, or layers.
    - Edges define how data flows between nodes (e.g., Angular → Gateway → Preprocessing).
    - At the end, we render the diagram to a PNG image and also save the raw DOT file,
    both in the current working directory.
    
"""

from graphviz import Digraph
import os

# Create directed graph with left-to-right orientation
dot = Digraph(
    comment="Tech Stack: Angular + Flask AI Wrapper with Two LLMs",
    graph_attr={"rankdir": "LR"}
)

# ---- Clusters for logical grouping ----

# Client cluster (Frontend)
with dot.subgraph(name="cluster_client") as c:
    c.attr(label="Client")
    c.node("Angular", "Angular Frontend (Upload, Controls, Quiz UI)")

# Backend API cluster (Flask)
with dot.subgraph(name="cluster_api") as c:
    c.attr(label="Backend API (Flask)")
    c.node("Gateway", "API Gateway / Router")
    c.node("Auth", "Auth & Rate Limit")
    c.node("Pre", "Preprocessing\n(PDF→MD, Clean, Chunk)")
    c.node("Embed", "Embeddings & RAG\n(FAISS/Qdrant)")
    c.node("Cache", "Cache (Redis)")
    c.node("Bus", "Shared Store / Content Bus")
    c.node("Router", "Decision Engine\n(Raw vs Summary vs Both)")
    c.node("Post", "Post-processing\n(Scoring, Dedup, JSON)")

# Model services cluster (LLMs)
with dot.subgraph(name="cluster_models") as c:
    c.attr(label="Model Services")
    c.node("LLM1", "LLM #1: Summarizer\n(Gemini/GPT/Claude or HF)")
    c.node("LLM2", "LLM #2: Question Gen\n(Gemini/T5/LLaMA)")

# Data layer cluster (Databases, Storage, Logs)
with dot.subgraph(name="cluster_data") as c:
    c.attr(label="Data Layer")
    c.node("DB", "Relational DB (Postgres/MySQL)\n(Metadata, Users, Logs)")
    c.node("Obj", "Object Storage (S3/Local)\n(PDFs, MD, Exports)")
    c.node("Obs", "Observability\n(Logs, Metrics)")

# ---- Edges (Data Flow) ----
dot.edge("Angular", "Gateway", label="HTTP")
dot.edge("Gateway", "Auth")
dot.edge("Gateway", "Pre", label="Upload PDF")
dot.edge("Pre", "Embed", label="Chunks + Embeddings")
dot.edge("Pre", "Bus", label="Clean Text / Sections")
dot.edge("Embed", "Router", label="Relevant Chunks")
dot.edge("Bus", "Router", label="Summary/Raw Availability")
dot.edge("Router", "LLM1", label="When summary needed")
dot.edge("LLM1", "Bus", label="Section Summaries / Keypoints")
dot.edge("Router", "LLM2", label="Context (raw/summary/chunks)")
dot.edge("LLM2", "Post", label="Q/A JSON, MCQs")
dot.edge("Post", "Cache")
dot.edge("Post", "DB", label="Persist")
dot.edge("Gateway", "Cache", label="Get/Set")
dot.edge("Gateway", "DB", label="Users, Jobs, Results")
dot.edge("Gateway", "Obj", label="Store/Fetch Files")
dot.edge("Gateway", "Obs", label="Tracing/Logs")
dot.edge("Post", "Obj", label="Exports (PDF/JSON)")
dot.edge("Gateway", "Angular", label="Results (Summary/Quiz JSON)")

# ---- Save Outputs in Images Folder ----

os.makedirs(os.path.join("Preprocessing", "images"), exist_ok=True)

# Save the diagram as PNG
out_path = os.path.join("Preprocessing", "images", "tech_stack_angular_flask_llm")
dot.render(out_path, format="png", cleanup=True)
dot_source_path = os.path.join("Preprocessing", "externalFolders", "tech_stack_angular_flask_llm.dot")

# Ensure folder exists
os.makedirs(os.path.dirname(dot_source_path), exist_ok=True)

with open(dot_source_path, "w", encoding="utf-8") as f:
    f.write(dot.source)
    

print("Saved files:")
print(" -", out_path + ".png")
print(" -", dot_source_path)

