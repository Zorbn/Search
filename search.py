import math
import os
import webbrowser
import time
import sys
import hashlib
from dataclasses import dataclass

# Values for different types of matches:
EXACT_TERM_VALUE = 1
PARTIAL_TERM_VALUE = 0.5

DELIMITERS = " "

MAX_RESULTS = 5

@dataclass
class Document:
    score: float
    path: str

def doc_terms_containing_term(term, doc):
    """
    Generate all of the terms in a document that contain
    the target term.
    """
    for doc_term in doc.lower().split(DELIMITERS):
        if term == doc_term:
            yield EXACT_TERM_VALUE
        elif term in doc_term:
            yield PARTIAL_TERM_VALUE

def term_frequency(term, doc):
    term = term.lower()

    num_of_target_term_in_doc = 0
    for value in doc_terms_containing_term(term, doc):
        num_of_target_term_in_doc += value

    terms_in_doc = doc.lower().split(DELIMITERS)
    len_of_doc = len(terms_in_doc)

    tf = num_of_target_term_in_doc / float(len_of_doc)

    return tf

def inverse_document_frequency(term, doc_list):
    term = term.lower()

    num_docs_with_target_term = 0

    for doc in doc_list:
        for value in doc_terms_containing_term(term, doc):
            num_docs_with_target_term += value
            break

    if num_docs_with_target_term == 0:
        return 0

    total_doc_count = len(doc_list)
    idf = math.log(total_doc_count / num_docs_with_target_term)

    return idf

def result_has_score(result):
    (_, document) = result
    return document.score > 0

def get_search_name(path, name, current_dir, use_full_path):
    if use_full_path:
        return f"{path}/{name}"
    else:
        # Ignore the file extension:
        # return os.path.splitext(name)[0]
        return name

def get_index_name(current_dir):
    script_path = os.path.realpath(os.path.dirname(__file__))
    dir_hash = hashlib.sha1(current_dir.encode("utf-8")).hexdigest()
    return f"{script_path}/index_{dir_hash}"

def index(current_dir):
    with open(get_index_name(current_dir), "w", encoding="utf-8") as file:
        for path, _, files in os.walk(current_dir):
            # Remove the current directory to save space in the index,
            # it will be the same for all documents so it doesn't matter.
            path = path[len(current_dir):]
            for name in files:
                file.write(f"{path}\n{name}\n")


def search(query, current_dir, force_reindex, use_full_path = False):
    doc_list = {}

    index_name = get_index_name(current_dir)
    if force_reindex or not os.path.isfile(index_name):
        index(current_dir)

    with open(index_name, "r", encoding="utf-8") as file:
        for path, name in zip(*[iter(file)]*2):
            # Remove \n from the path and names
            path = path[:-1]
            name = name[:-1]

            search_name = get_search_name(path, name, current_dir, use_full_path)
            doc_list[search_name] = Document(0, f"{path}/{name}")

    for term in query.lower().split(DELIMITERS):
        idf = inverse_document_frequency(term, doc_list)

        for doc in doc_list:
            points = idf * term_frequency(term, doc)
            doc_list[doc].score += points

    # Get rid of results with a score of 0.
    doc_list = dict(filter(result_has_score, doc_list.items()))

    return doc_list

def main():
    current_dir = os.getcwd()

    if len(sys.argv) > 1:
        current_dir = sys.argv[1]

    # Use consistent slashes:
    current_dir = current_dir.replace(os.sep, "/")

    force_reindex = "-r" in sys.argv or "--reindex" in sys.argv

    print("Query: ", end="")
    query = input()

    search_start = time.time()
    results = search(query, current_dir, force_reindex)

    if len(results) == 0:
        print("Found no matching names, expanding search...")
        results = search(query, current_dir, force_reindex, use_full_path=True)

    search_end = time.time()
    search_time = search_end - search_start

    result_count = len(results)
    print(f"Found {result_count} results in {search_time:.2f} seconds.")

    sorted_results = sorted(results.items(), key=lambda x: x[1].score, reverse=True)

    result_i = 0
    for result in sorted_results[0:MAX_RESULTS]:
        result_i += 1
        (_, document) = result

        # Use consistent slashes and skip leading slash:
        formatted_path = document.path.replace(os.sep, "/")[1:]
        print(f"{result_i}: {formatted_path}")

    print(f"Open a file (1-{MAX_RESULTS})? ")
    choice = input()

    if not choice.isdigit():
        return

    chosen_result = int(choice) - 1

    # Filter out results that aren't in the list.
    if chosen_result >= MAX_RESULTS or chosen_result >= result_count or chosen_result < 0:
        return

    (chosen_name, chosen_document) = sorted_results[chosen_result]
    print(f"Opening {chosen_name}...")
    full_chosen_path = current_dir + chosen_document.path
    webbrowser.open(full_chosen_path)

if __name__ == "__main__":
    main()