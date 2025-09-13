"""
    This script uses Graphviz to draw the Angular Frontend Architecture
    for a Summarization + Question Generation app.

    - Uses Digraph from graphviz with rankdir=LR.
    - Groups related components into clusters (App Shell, Pages, Upload, Results, Shared UI, Services).
    - Adds nodes for components and defines edges for data flow.
    - Saves both the PNG diagram and the DOT source in the current folder.
"""

from graphviz import Digraph
import os

# Create directed graph with left-to-right orientation
dot = Digraph(
    comment="Angular Frontend Architecture",
    graph_attr={"rankdir": "LR", "fontsize": "10", "labelloc": "t", "label": "Angular Frontend: Components & Flow (Summarize | Question Gen)"}
)
dot.attr("node", shape="box", fontsize="10")

# ---- Clusters ----

# App shell
with dot.subgraph(name="cluster_app") as c:
    c.attr(label="App Shell", style="rounded")
    c.node("AppComponent", "AppComponent\n(app-root)")
    c.node("Navbar", "NavbarComponent")
    c.node("Sidebar", "SidebarComponent")
    c.node("RouterOutlet", "RouterOutlet")
    c.edges([("AppComponent", "Navbar"),
             ("AppComponent", "Sidebar"),
             ("AppComponent", "RouterOutlet")])

# Pages / Routes
with dot.subgraph(name="cluster_pages") as c:
    c.attr(label="Pages / Routes", style="rounded")
    c.node("HomePage", "HomePageComponent\n(/)")
    c.node("UploadPage", "UploadPageComponent\n(/upload)")
    c.node("ProcessPage", "ProcessPageComponent\n(/process)")
    c.node("ResultsPage", "ResultsPageComponent\n(/results)")
    c.node("HistoryPage", "HistoryPageComponent\n(/history)")

# Upload & Controls
with dot.subgraph(name="cluster_upload") as c:
    c.attr(label="Upload & Controls", style="rounded")
    c.node("FileUpload", "FileUploadComponent\n(Drag & Drop / Picker)")
    c.node("ModeSelector", "ModeSelectorComponent\n(Summary | QGen | Both)")
    c.node("SettingsPanel", "SettingsPanelComponent\n(Length, #Qs, Difficulty)")
    c.node("ChunkPreview", "SharedContentPreviewComponent\n(Preview cleaned/chunked text)")

# Results
with dot.subgraph(name="cluster_results") as c:
    c.attr(label="Results View", style="rounded")
    c.node("SummaryViewer", "SummaryViewerComponent\n(Sectioned / Highlights)")
    c.node("QuizDashboard", "QuizDashboardComponent\n(JEE-style)")
    c.node("QuestionList", "QuestionListComponent")
    c.node("MCQCard", "MCQCardComponent\n(single/multi-correct)")
    c.node("Explanation", "ExplanationPanelComponent\n(Answer & rationale)")

# Shared UI
with dot.subgraph(name="cluster_ui") as c:
    c.attr(label="Shared UI", style="rounded")
    c.node("Loader", "LoaderComponent\n(Progress/Status)")
    c.node("ErrorToast", "ErrorToastComponent")
    c.node("ExportButtons", "ExportButtonsComponent\n(PDF/JSON/Copy)")
    c.node("FeedbackWidget", "FeedbackWidgetComponent\n(Useful? Rating)")
    c.node("Paginator", "PaginatorComponent")
    c.node("SearchBar", "SearchBarComponent")
    c.node("TagChips", "TagChipsComponent\n(keywords/NER tags)")

# Services
with dot.subgraph(name="cluster_services") as c:
    c.attr(label="Client Services & State (Angular)", style="rounded")
    c.node("ApiService", "ApiService\n(HTTP to Flask)")
    c.node("UploadService", "UploadService\n(file status)")
    c.node("StateStore", "StateStore (NgRx/Signals)\n(session, doc, results)")
    c.node("CacheService", "CacheService\n(local/session storage)")
    c.node("GuardAuth", "AuthGuard")
    c.node("Interceptor", "HttpInterceptor\n(spinners, errors, auth)")

# ---- Edges ----

# Routing
dot.edges([("RouterOutlet", "HomePage"),
           ("RouterOutlet", "UploadPage"),
           ("RouterOutlet", "ProcessPage"),
           ("RouterOutlet", "ResultsPage"),
           ("RouterOutlet", "HistoryPage")])

# Page composition
dot.edges([("UploadPage", "FileUpload"),
           ("UploadPage", "ModeSelector"),
           ("UploadPage", "SettingsPanel"),
           ("UploadPage", "ChunkPreview")])

dot.edges([("ProcessPage", "Loader"),
           ("ProcessPage", "ErrorToast")])

dot.edges([("ResultsPage", "SummaryViewer"),
           ("ResultsPage", "QuizDashboard"),
           ("ResultsPage", "ExportButtons"),
           ("ResultsPage", "FeedbackWidget")])

dot.edges([("QuizDashboard", "SearchBar"),
           ("QuizDashboard", "TagChips"),
           ("QuizDashboard", "QuestionList")])
dot.edge("QuestionList", "MCQCard")
dot.edge("QuestionList", "Paginator")
dot.edge("MCQCard", "Explanation")

# Service wiring
dot.edge("FileUpload", "UploadService")
dot.edge("UploadService", "ApiService", label="init upload/create job")
dot.edge("ModeSelector", "StateStore", label="mode = summary|qgen|both")
dot.edge("SettingsPanel", "StateStore", label="params (length,#Qs,level)")
dot.edge("ChunkPreview", "StateStore", label="reads preprocessed preview")

dot.edge("ProcessPage", "ApiService", label="start processing")
dot.edge("ApiService", "Interceptor", label="auto attach auth / handle errors")
dot.edge("ApiService", "StateStore", label="persist job status/results")
dot.edge("StateStore", "ResultsPage", label="bind summary & quiz JSON")

# History & caching
dot.edge("HistoryPage", "StateStore")
dot.edge("HistoryPage", "CacheService")

# Guards
dot.edge("GuardAuth", "RouterOutlet", label="protect /process, /results")

# UI feedback
dot.edge("Interceptor", "Loader", label="show/hide")
dot.edge("Interceptor", "ErrorToast", label="notify")

# ---- Save Outputs ----
png_path = "frontend_architecture"
dot.render(png_path, format="png", cleanup=True)

with open("frontend_architecture.dot", "w", encoding="utf-8") as f:
    f.write(dot.source)

print("Saved frontend_architecture.png and frontend_architecture.dot in current folder")
