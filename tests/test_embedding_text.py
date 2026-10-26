from mechragnic.embedding.text import text_for_embedding


def test_solutions_are_left_out_by_default():
    text = text_for_embedding(["noise"], ["worn belt"], ["replace belt"])

    assert text == "Symptoms: noise\nCauses: worn belt"


def test_solutions_are_included_on_request():
    text = text_for_embedding(["noise"], ["worn belt"], ["replace belt"], include_solutions=True)

    assert text == "Symptoms: noise\nCauses: worn belt\nSolution: replace belt"


def test_items_after_the_first_are_dashed():
    # The stored embeddings were computed with this exact format, first item without a dash.
    text = text_for_embedding(["squeal", "smell"], ["belt", "pulley"], [])

    assert text == "Symptoms: squeal\n- smell\nCauses: belt\n- pulley"


def test_prefix_goes_first():
    text = text_for_embedding(["noise"], ["belt"], [], prefix="search_document: ")

    assert text.startswith("search_document: Symptoms: noise")
