# RDF text compression experiment

Experiment in compressing RDF text formats such as N-Triples using off-the-shelf compressors such as gzip

See the [accompanying blog post](https://minorgordon.net/blog/2024/06/21/rdf-text-compression-experiment.html) for a summary of the experiment and key findings.

## Prerequisites

### Required

* Python 3

### Optional

Command line programs:

* bzip2
* gzip
* [Brotli](https://github.com/google/brotli)
* [Rapper](https://librdf.org/raptor/rapper.html)

## Running

Populate the `input` directory with RDF serialized as [N-Triples](). The files must have the extension `.nt`.

Run the script:

    python3 experiment.py

## Results

The results of running the experiment on a variety of off-the-shelf RDF datasets are in [results.csv](./results.csv).