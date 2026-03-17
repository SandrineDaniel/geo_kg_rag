# 🌍 Geo-KG-RAG

From web data to a knowledge graph-powered AI assistant for geopolitical analysis.

---

## 📌 Project Overview

This project aims to transform unstructured web data into a structured **Knowledge Graph (KG)** and use it to support an AI assistant through **Retrieval-Augmented Generation (RAG)**.

The pipeline follows an end-to-end approach:

* Web data collection
* Text preprocessing
* Information extraction (entities & relations)
* Knowledge graph construction (RDF)
* Entity linking & graph expansion
* Knowledge Graph Embedding (KGE)
* Reasoning (rules + embeddings)
* AI assistant integration

---

## 🧠 Objectives

* Convert raw web content into structured knowledge
* Build a domain-specific knowledge graph (geopolitics: Greenland, Europe, military context)
* Improve reasoning using:

  * Rule-based inference (SWRL)
  * Embedding-based reasoning (KGE)
* Evaluate knowledge graph quality through link prediction tasks
* Reduce hallucinations in AI systems using grounded knowledge

---

## 🏗️ Project Structure

```
.
├── data/                # Raw and processed datasets
├── notebooks/           # Exploration and debugging notebooks
├── src/                 # Core pipeline modules
├── outputs/             # Generated files (triples, graphs, embeddings)
├── scripts/             # Pipeline execution scripts
├── reports/             # Project report
├── requirements.txt
└── README.md
```

---

## 🔄 Pipeline

### 1. Web Mining

* Crawl and extract textual content from news articles

### 2. Information Extraction

* Named Entity Recognition (NER) using spaCy
* Relation extraction (rule-based)

### 3. Knowledge Graph Construction

* Triples generation (subject, predicate, object)
* RDF graph creation using `rdflib`

### 4. Entity Linking & Expansion

* Alignment with DBpedia
* Graph enrichment using external knowledge bases

### 5. Knowledge Graph Embedding (KGE)

* Models: TransE, DistMult, ComplEx (via PyKEEN)
* Dataset preparation (train/valid/test split)
* Link prediction evaluation:

  * MRR
  * Hits@K

### 6. Reasoning

* Rule-based reasoning (SWRL + OWLReady2)
* Embedding-based reasoning
* Comparison between symbolic and vector-based inference

---

## 📊 Experiments

* Model comparison (TransE vs DistMult vs ComplEx)
* Impact of knowledge graph size
* Embedding analysis:

  * Nearest neighbors
  * Clustering (t-SNE)
  * Relation behavior

---

## ⚙️ Technologies Used

* Python
* spaCy
* RDFLib
* OWLReady2
* PyKEEN
* DBpedia / Wikidata

---

## 📁 Outputs

* Extracted entities and relations
* RDF knowledge graphs (.ttl)
* Aligned and expanded knowledge base
* Embedding models and evaluation results

---

## ⚠️ Challenges

* Noisy and unstructured web data
* Weak relation extraction from text
* Predicate alignment difficulties
* Impact of KB quality on embeddings

---

## 🚀 Future Work

* Improve relation extraction (more robust NLP methods)
* Better ontology design
* Full RAG assistant integration
* Interactive querying interface

---

## 👩‍💻 Authors

* Raphael Marques Araujo
* Sandrine Daniel

---

## 📚 Course Context

This project is part of the course:
**Web Data Mining & Semantics**
