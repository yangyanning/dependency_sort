import os
import subprocess
from collections import defaultdict, deque
import graphviz

def is_shared_library(filename):
    """
    Check if a file is a shared library (.so or .so.*).
    """
    return filename.endswith(".so") or ".so." in filename

def resolve_symlinks(directory):
    """
    Resolve symlinks and treat them as dependencies.
    Returns:
        - A map of symlinks to their immediate targets
        - A list of resolved shared libraries
    """
    symlink_map = {}
    shared_libraries = []

    for filename in os.listdir(directory):
        filepath = os.path.join(directory, filename)
        if os.path.islink(filepath):
            # Use os.readlink() to get the immediate target of the symlink
            target = os.readlink(filepath)
            symlink_map[filename] = target
        if is_shared_library(filename):
            shared_libraries.append(filename)

    return symlink_map, shared_libraries

def get_dependencies(lib_path, available_libraries):
    """
    Get the shared library dependencies for a given .so file using readelf,
    but only include dependencies available in the working directory.
    """
    try:
        output = subprocess.check_output(["readelf", "-d", lib_path], text=True)
        dependencies = []
        for line in output.splitlines():
            if "NEEDED" in line:
                dep = line.split("[")[1].split("]")[0]
                if dep in available_libraries:
                    dependencies.append(dep)
        return dependencies
    except subprocess.CalledProcessError as e:
        print(f"Error reading dependencies for {lib_path}: {e}")
        return []

def build_dependency_graph(directory):
    """
    Build a dependency graph of shared libraries in the directory,
    including symlinks as dependencies.
    """
    symlink_map, shared_libraries = resolve_symlinks(directory)
    available_libraries = set(shared_libraries)

    dependency_graph = defaultdict(list)

    # Add dependencies from symlinks
    for symlink, target in symlink_map.items():
        if target in available_libraries:
            dependency_graph[symlink].append(target)

    # Add dependencies from readelf
    for lib in shared_libraries:
        lib_path = os.path.join(directory, lib)
        dependencies = get_dependencies(lib_path, available_libraries)
        dependency_graph[lib].extend(dependencies)

    return dependency_graph

def topological_sort(dependency_graph):
    """
    Perform a topological sort on the dependency graph.
    """
    in_degree = {node: 0 for node in dependency_graph}
    for deps in dependency_graph.values():
        for dep in deps:
            in_degree[dep] += 1

    # Start with nodes with no dependencies
    queue = deque([node for node, degree in in_degree.items() if degree == 0])
    sorted_libraries = []

    while queue:
        lib = queue.popleft()
        sorted_libraries.append(lib)
        for dep in dependency_graph[lib]:
            in_degree[dep] -= 1
            if in_degree[dep] == 0:
                queue.append(dep)

    if len(sorted_libraries) != len(dependency_graph):
        raise ValueError("Cycle detected in the dependency graph!")

    return sorted_libraries

def visualize_dependency_graph(dependency_graph, output_file="dependency_graph"):
    """
    Visualize the dependency graph using graphviz.
    """
    dot = graphviz.Digraph(format="png")
    dot.attr(rankdir="LR")  # Set left-to-right layout

    for library, dependencies in dependency_graph.items():
        for dep in dependencies:
            dot.edge(library, dep)

    dot.render(output_file)
    print(f"Dependency graph saved as {output_file}.png")

def main(directory):
    """
    Main function to build and visualize the dependency graph,
    and perform topological sort.
    """
    dependency_graph = build_dependency_graph(directory)

    print("Performing topological sort of dependencies...")
    sorted_libraries = topological_sort(dependency_graph)
    print("Topological sort result:")
    for lib in sorted_libraries:
        print(lib)

    visualize_dependency_graph(dependency_graph)

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <directory>")
        sys.exit(1)
    main(sys.argv[1])
