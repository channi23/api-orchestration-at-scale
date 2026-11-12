# BM25 shortlist baseline (model-free)

Share of the 100 frozen tasks whose gold tool is inside the top-k of a BM25 ranking of the catalog. 'card' indexes tool name + description only; 'all' adds parameter names and descriptions from the schema.

| Indexed text | Catalog size | recall@1 | recall@3 | recall@5 | recall@10 | MRR |
|---|---:|---:|---:|---:|---:|---:|
| card | 20 | 98% | 100% | 100% | 100% | 0.990 |
| card | 50 | 95% | 100% | 100% | 100% | 0.973 |
| card | 100 | 93% | 100% | 100% | 100% | 0.957 |
| all | 20 | 97% | 100% | 100% | 100% | 0.983 |
| all | 50 | 95% | 99% | 99% | 100% | 0.970 |
| all | 100 | 95% | 98% | 99% | 100% | 0.969 |

Reading: recall@1 is what BM25 alone would score as a selector. recall@5 is the ceiling of a 'shortlist 5, then let the model choose and fill arguments' pipeline. The tool names and descriptions were written by the experimenter, so absolute values are specific to this benchmark.
