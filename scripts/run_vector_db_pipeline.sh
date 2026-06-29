#!/bin/bash
python -m scripts.embed_chunks --limit 1000000 --embedding-context title_path
python -m scripts.build_vector_index --limit 1000000
