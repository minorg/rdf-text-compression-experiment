import csv
from os import stat
from pathlib import Path
from shutil import which, rmtree
from subprocess import check_call
from typing import Callable

Compressor = Callable[[Path, Path], Path]

def combine_compressors(left_compressor: Compressor, right_compressor: Compressor) -> Compressor:
    def combined_compressor(input_file_path: Path, output_directory_path: Path) -> None:
        return right_compressor(left_compressor(input_file_path, output_directory_path), output_directory_path)
    return combined_compressor


def compressors_by_name() -> dict[str, Compressor]:
    compressors_by_name_: dict[str, Compressor] = {}

    def ttl_compressor(input_file_path: Path, output_directory_path: Path) -> Path:
        output_file_path = (output_directory_path / f"{input_file_path.stem}.ttl")
        args = ["rapper", "-i", "ntriples", "-o", "turtle", str(input_file_path)]
        for namespace_prefix, namespace_uri in {
            "dcat": "http://www.w3.org/ns/dcat#",
            "dct": "http://purl.org/dc/terms/",
            "owl": "http://www.w3.org/2002/07/owl#",
            "meshv": "http://id.nlm.nih.gov/mesh/vocab#",
            "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
            "skos": "http://www.w3.org/2004/02/skos/core#",
            "skos-thes": "http://purl.org/iso25964/skos-thes#",
            "skos-xl": "http://www.w3.org/2008/05/skos-xl#",
            "xkos": "http://rdf-vocabulary.ddialliance.org/xkos#",
            "xsd": "http://www.w3.org/2001/XMLSchema#"
        }.items():
            args.extend(("-f", f"xmlns:{namespace_prefix}=\"{namespace_uri}\""))
        with output_file_path.open("w+") as output_file:
            # args = −f ’xmlns:prefix="uri"’
            check_call(args, stdout=output_file)
        return output_file_path

    if which("gzip"):
        def gzip_compressor(input_file_path: Path, output_directory_path: Path) -> Path:
            output_file_path = (output_directory_path / f"{input_file_path.stem}.gz")
            with output_file_path.open("w+b") as output_file:
                check_call(["gzip", "-9", "--keep", "--stdout", str(input_file_path)], stdout=output_file)
            return output_file_path

        compressors_by_name_["gzip"] = gzip_compressor

    if which("rapper"):
        for other_compressor_name, other_compressor in tuple(compressors_by_name_.items()):
            compressors_by_name_["Turtle " + other_compressor_name] = combine_compressors(ttl_compressor, other_compressor)
        compressors_by_name_["Turtle"] = ttl_compressor

    return compressors_by_name_


def main() -> None:
    root_directory_path = Path(__file__).parent.absolute()
    output_directory_path = root_directory_path / "output"
    rmtree(output_directory_path)
    output_directory_path.mkdir(parents=True)

    nt_file_paths: list[Path] = []
    for input_directory_path, _, input_file_names in (root_directory_path / "input").walk():
        for input_file_name in sorted(input_file_names):
            if input_file_name[0] == ".":
                continue
            if not input_file_name.lower().endswith(".nt"):
                continue
            # if input_file_name == "unesco-thesaurus.nt":
            #     continue
            nt_file_paths.append(input_directory_path / input_file_name)

    compressors_by_name_ = compressors_by_name()

    with (root_directory_path / "results.csv").open("w+") as results_csv_file:
        csv_writer = csv.DictWriter(results_csv_file, fieldnames=["Input", "N-Triples", *compressors_by_name_.keys()])
        csv_writer.writeheader()
        for nt_file_path in nt_file_paths:
            csv_row = {"Input": nt_file_path.stem, "N-Triples": stat(nt_file_path).st_size}
            for compressor_name, compressor in compressors_by_name_.items():
                print("compressing", nt_file_path, "with", compressor_name)
                output_file_path = compressor(nt_file_path, output_directory_path)
                output_file_size= stat(output_file_path).st_size
                print("compressed", nt_file_path, "with", compressor_name, "to", output_file_path, ":", output_file_size, "bytes")
                csv_row[compressor_name] = str(output_file_size)
            csv_writer.writerow(csv_row)


if __name__ == "__main__":
    main()