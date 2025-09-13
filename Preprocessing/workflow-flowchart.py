from graphviz import Digraph
import os

# Create a directed graph
dot = Digraph(comment="Full-Stack AI Wrapper with Two LLMs")

# Nodes
dot.node("U", "User Input (PDF/Query)")
dot.node("FE", "Frontend (UI for Upload & Settings)")
dot.node("BE", "Backend API (Request Orchestration)")
dot.node("P", "Preprocessing (PDF → Markdown, Cleaning)")
dot.node("WR", "Wrapper Logic (Decision Engine)")
dot.node("L1", "LLM 1 (Summarizer)")
dot.node("L2", "LLM 2 (Question Generator / Final Output)")
dot.node("DB", "Database (Cache + Logs)")
dot.node("O", "Final Output to User")

# Edges
dot.edges([("U", "FE"), ("FE", "BE"), ("BE", "P")])
dot.edge("P", "WR")
dot.edge("WR", "L1", label="If Summarization Needed")
dot.edge("WR", "L2", label="If Raw or Post-Summarization")
dot.edge("L1", "L2", label="Pass Summary")
dot.edge("L2", "BE", label="Return Generated Output")
dot.edge("WR", "DB", label="Store Decisions & Metadata")
dot.edge("BE", "O")

# Create images directory if it doesn't exist
os.makedirs(os.path.join("Preprocessing", "images"), exist_ok=True)


# Save and render in images folder
file_path = os.path.join("Preprocessing", "images", "fullstack_ai_wrapper_flowchart")
dot.render(file_path, format="png", cleanup=True)

print("Saved:", file_path + ".png")
