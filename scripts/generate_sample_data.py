import json
from pathlib import Path

SAMPLE_DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "sample_playlist.json"

MODULES = [
    ("Python Fundamentals", 15, 180, 480),
    ("Object-Oriented Programming & Design Patterns", 15, 300, 720),
    ("Data Structures & Algorithms in Python", 20, 240, 900),
    ("Relational Databases & SQLAlchemy ORM", 15, 360, 840),
    ("Flask Web Architecture & REST APIs", 15, 420, 1020),
    ("Concurrency, Threading & Async Processing", 15, 300, 780),
    ("Testing, Pytest, Mocking & Code Quality", 10, 240, 600),
]

TOPICS = [
    # Module 1
    "Variables, Data Types, and Type Hinting", "Control Flow, Loops, and Iteration Idioms",
    "Functions, Arguments, Keyword Unpacking, and Scopes", "Decorators, Closures, and Higher-Order Functions",
    "Generators, Iterators, and Yield Expressions", "List, Dict, and Set Comprehensions",
    "Context Managers and the with Statement", "Exception Hierarchy and Defensive Handling",
    "String Formatting, Regex, and Text Parsing", "Working with Files and Pathlib",
    "Modules, Packages, and Imports Deep Dive", "Virtual Environments and Pip Management",
    "Datetime and Timezone Best Practices", "JSON and Serialization Techniques",
    "Standard Library Hidden Gems",

    # Module 2
    "Classes, Objects, and Self Mechanism", "Dunder Methods and Operator Overloading",
    "Inheritance, Composition, and MRO", "Abstract Base Classes and Interfaces",
    "Dataclasses and Pydantic Comparison", "Encapsulation and Property Decorators",
    "Singleton and Factory Method Patterns", "Observer Pattern and Event Dispatching",
    "Strategy Pattern for Swappable Algorithms", "Adapter Pattern for Legacy System Wrap",
    "Decorator Pattern in Class Architecture", "State Pattern for Finite State Machines",
    "Command Pattern for Undoable Operations", "Dependency Injection Principles",
    "Refactoring Procedural Code to OOP",

    # Module 3
    "Big-O Time and Space Complexity Analysis", "Dynamic Arrays and Amortized Analysis",
    "Singly and Doubly Linked Lists", "Stack Implementation and Balancing Equations",
    "Queue and Double-Ended Queue (Deque)", "Hash Tables and Collision Resolution",
    "Binary Search and Boundary Scanning", "Binary Search Trees (BST) Insertion and Deletion",
    "Tree Traversals: Inorder, Preorder, Postorder", "Heap and Priority Queue Applications",
    "Graph Representations: Adjacency List vs Matrix", "Breadth-First Search (BFS) Traversal",
    "Depth-First Search (DFS) Traversal", "Dijkstra's Shortest Path Algorithm",
    "Recursion and Memoization Strategies", "Dynamic Programming: Knapsack Problem",
    "Sorting: QuickSort and MergeSort Explained", "Two Pointer Technique for String & Array Problems",
    "Sliding Window Algorithm Patterns", "Trie Data Structure for Autocomplete Systems",

    # Module 4
    "Relational Database Fundamentals & Normalization", "SQLite Architecture and Transaction Models",
    "SQL Select, Joins, Group By, and Aggregations", "Database Indexing, B-Trees, and Query Plans",
    "Foreign Keys, Constraints, and Data Integrity", "ACID Properties and Isolation Levels",
    "SQLAlchemy 2.0 Core vs ORM Patterns", "Declarative Base and Model Definitions",
    "One-to-Many Relationships and Cascades", "Many-to-Many Association Tables",
    "Session Lifecycles, Unit of Work, and Flushes", "Thread-Safe Sessions in Multi-Threaded Apps",
    "Query Optimization and N+1 Problem Prevention", "Database Migrations and Schema Versioning",
    "Safe Transaction Rollbacks on Application Errors",

    # Module 5
    "WSGI, ASGI, and Web Server Gateways", "Flask Application Factory Pattern",
    "Blueprints and Modular Routing Architecture", "Handling Requests, Headers, and Query Parameters",
    "Building RESTful JSON Endpoints", "HTTP Status Codes and Error Handlers",
    "Template Rendering with Jinja2 and Macros", "Form Handling, CSRF Protection, and Validation",
    "Static Assets, Caching, and CDN Strategy", "Server-Sent Events (SSE) for Real-Time Feeds",
    "Session Management and Cookie Security", "Middleware and Request Hooks (before/after_request)",
    "API Authentication Patterns and Tokens", "Rate Limiting and Throttling Requests",
    "Production Readiness with Gunicorn and Waitress",

    # Module 6
    "Processes vs Threads vs Coroutines in Python", "The Global Interpreter Lock (GIL) Explained",
    "Threading Module: Thread Spawning and Joining", "Thread Synchronization: Locks and RLocks",
    "Condition Variables and Thread Signaling", "Producer-Consumer Pattern with Queue.Queue",
    "Daemon Threads vs Non-Daemon Worker Lifecycles", "Graceful Worker Shutdown and Poison Pills",
    "Subprocess Execution: Popen, Pipes, and Deadlocks", "Simulating Network Interruptions and Jitter",
    "Exponential Backoff and Retry Strategies", "Idempotency in Distributed Job Processing",
    "Crash Recovery and State Reconciliation", "Thread-Safe In-Memory Queue State Management",
    "Deadlock Prevention and Timeout Coordination",

    # Module 7
    "Testing Philosophy: Unit, Integration, and E2E", "Getting Started with Pytest and Assertions",
    "Pytest Fixtures and Dependency Injection", "Database Testing with In-Memory SQLite",
    "Mocking External APIs with Unittest.mock", "Testing Background Worker Threads Safely",
    "Code Coverage Analysis and Reporting", "Parameterizing Tests for Edge Case Coverage",
    "Defensive Exception Testing and Validation", "Continuous Integration Workflows and Linting",
]

def generate_sample_playlist():
    items = []
    video_idx = 1
    duration_seed = [245, 360, 480, 520, 610, 750, 310, 890, 420, 600, 330, 950, 410, 570, 640]

    for topic in TOPICS:
        duration = duration_seed[(video_idx * 7) % len(duration_seed)] + ((video_idx * 13) % 180)
        source_id = f"demo_vid_{video_idx:03d}"
        
        # Determine module name
        if video_idx <= 15:
            module = "Python Fundamentals"
        elif video_idx <= 30:
            module = "Object-Oriented Programming"
        elif video_idx <= 50:
            module = "Data Structures & Algorithms"
        elif video_idx <= 65:
            module = "Relational Databases & SQLAlchemy"
        elif video_idx <= 80:
            module = "Flask Web Architecture"
        elif video_idx <= 95:
            module = "Concurrency & Queue Engineering"
        else:
            module = "Testing & Code Quality"

        item = {
            "position": video_idx,
            "source_id": source_id,
            "title": f"#{video_idx:03d} - {topic}",
            "duration_seconds": duration,
            "media_type": "video",
            "availability_status": "available",
            "thumbnail_url": f"/static/images/placeholder-thumbnail.svg",
            "metadata": {
                "module": module,
                "author": "PlaylistPilot Educational Series",
                "resolution": "1080p",
                "estimated_size_mb": round((duration * 1.5) / 10, 1),
                "is_demo": True,
                "tags": ["python", "mca-project", "algorithms", "architecture"]
            }
        }
        items.append(item)
        video_idx += 1

    playlist_data = {
        "title": "Mastering Advanced Python & Systems Architecture (105 Lectures)",
        "source_type": "demo",
        "source_id": "PL_DEMO_MCA_PYTHON_2026",
        "source_url": "https://playlistpilot.local/demo/python-masterclass",
        "description": "Comprehensive MCA-curated 105-video educational playlist designed for demonstration of queue processing, interruption recovery, priority management, and state persistence.",
        "thumbnail_url": "/static/images/placeholder-thumbnail.svg",
        "item_count": len(items),
        "items": items
    }

    SAMPLE_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(SAMPLE_DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(playlist_data, f, indent=2)

    print(f"Successfully generated {len(items)} sample playlist items at {SAMPLE_DATA_PATH}")

if __name__ == "__main__":
    generate_sample_playlist()
