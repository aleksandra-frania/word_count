import os
import re
import fitz
import spacy
import streamlit as st
from collections import Counter, defaultdict

def install_spacy_model(model_name):
    try:
        spacy.load(model_name)
    except OSError:
        st.write(f"Model {model_name} not found. Installing...")
        os.system(f"python -m spacy download {model_name}")
        spacy.load(model_name)

# Install necessary models if not already installed
install_spacy_model("de_core_news_sm")
install_spacy_model("fr_core_news_sm")

def clean_text(text):
    text = re.sub(r'[^a-zA-Zéàèùâêîôûëïüçßöäü\s-]', '', text)
    text = re.sub(r"\b\w'", '', text)
    return text.lower()

def lemmatize_words(words, nlp):
    lemma_dict = defaultdict(set)
    lemma_counts = Counter()
    
    doc = nlp(" ".join(words))
    for token in doc:
        if token.is_alpha and token.pos_ in {"NOUN", "VERB", "ADJ"} and len(token.text) > 1:  # Keep only content words
            lemma_dict[token.lemma_].add(token.text)
            lemma_counts[token.lemma_] += 1
    
    return lemma_dict, lemma_counts

def flatten_pdf(input_pdf, output_pdf):
    doc = fitz.open(input_pdf)
    doc.save(output_pdf, garbage=4, deflate=True, clean=True)
    doc.close()

def process_pdf(uploaded_file, language):
    if language == "de":
        nlp = spacy.load("de_core_news_sm")
    elif language == "fr":
        nlp = spacy.load("fr_core_news_sm")
    else:
        st.error("Invalid language selection.")
        return [], ""

    with open(uploaded_file.name, "wb") as temp_pdf:
        temp_pdf.write(uploaded_file.getbuffer())
    temp_pdf_path = temp_pdf.name

    flattened_pdf = f"flattened_{os.path.splitext(uploaded_file.name)[0]}.pdf"
    flatten_pdf(temp_pdf_path, flattened_pdf)

    doc = fitz.open(flattened_pdf)
    all_words = []

    for page in doc:
        text = page.get_text("text")
        cleaned_text = clean_text(text)
        words = cleaned_text.split()
        all_words.extend(words)

    doc.close()
    os.remove(temp_pdf_path)
    os.remove(flattened_pdf)

    lemma_dict, lemma_counts = lemmatize_words(all_words, nlp)
    sorted_lemmas = sorted(lemma_counts.items(), key=lambda item: item[1], reverse=True)

    csv_data = [["Word Variants", "Count"]]
    for lemma, count in sorted_lemmas:
        word_variants = "/".join(sorted(lemma_dict[lemma]))
        csv_data.append([word_variants, count])

    return csv_data, uploaded_file.name

def main():
    st.title("Word Counter (de/fr)")
    st.write("Upload a German or French PDF to analyze word frequencies with lemmatization.")

    uploaded_file = st.file_uploader("Upload a PDF", type=["pdf"])
    language = st.radio("Select document language:", ("de", "fr"))

    if uploaded_file and language:
        st.write("Processing file...")
        csv_data, original_file_name = process_pdf(uploaded_file, language)
        
        st.write("### Word Frequency Results")
        st.dataframe(csv_data[1:], use_container_width=True)  # Display results in a table (excluding header)

        # Allow CSV download
        csv_string = "\n".join([",".join(map(str, row)) for row in csv_data])
        csv_file_name = f"{os.path.splitext(original_file_name)[0]}_word_count.csv"
        st.download_button("Download CSV", csv_string, csv_file_name, "text/csv")

if __name__ == "__main__":
    main()
