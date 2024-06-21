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

    if which("brotli"):
        def brotli_compressor(input_file_path: Path, output_directory_path: Path) -> Path:
            output_file_path = (output_directory_path / f"{input_file_path.name}.br")
            with output_file_path.open("w+b") as output_file:
                check_call(["brotli", "--keep", "-q", "11", "--stdout", str(input_file_path)], stdout=output_file)
            return output_file_path

        compressors_by_name_["brotli"] = brotli_compressor

    if which("bzip2"):
        def bzip2_compressor(input_file_path: Path, output_directory_path: Path) -> Path:
            output_file_path = (output_directory_path / f"{input_file_path.name}.bz2")
            with output_file_path.open("w+b") as output_file:
                check_call(["bzip2", "-9", "--keep", "--stdout", str(input_file_path)], stdout=output_file)
            return output_file_path

        compressors_by_name_["bzip2"] = bzip2_compressor

    if which("gzip"):
        def gzip_compressor(input_file_path: Path, output_directory_path: Path) -> Path:
            output_file_path = (output_directory_path / f"{input_file_path.name}.gz")
            with output_file_path.open("w+b") as output_file:
                check_call(["gzip", "-9", "--keep", "--stdout", str(input_file_path)], stdout=output_file)
            return output_file_path

        compressors_by_name_["gzip"] = gzip_compressor

    return compressors_by_name_


def sizeof_fmt(num, suffix="B"):
    for unit in ("", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"):
        if abs(num) < 1024.0:
            return f"{num:3.1f}{unit}{suffix}"
        num /= 1024.0
    return f"{num:.1f}Yi{suffix}"


def main() -> None:
    root_directory_path = Path(__file__).parent.absolute()
    output_directory_path = root_directory_path / "output"
    rmtree(output_directory_path)
    output_directory_path.mkdir(parents=True)

    have_rapper = bool(which("rapper"))

    inputs: dict[str, dict[str, Path]] = {}
    for input_directory_path, _, input_file_names in (root_directory_path / "input").walk():
        for input_file_name in sorted(input_file_names):
            if input_file_name[0] == ".":
                continue
            if not input_file_name.lower().endswith(".nt"):
                continue
            # if input_file_name == "unesco-thesaurus.nt":
            #     continue
            nt_file_path = input_directory_path / input_file_name
            inputs[nt_file_path.stem] = {"N-Triples": nt_file_path}

            if have_rapper:
                ttl_file_path = (output_directory_path / f"{nt_file_path.stem}.ttl")
                args = ["rapper", "-i", "ntriples", "-o", "turtle", str(nt_file_path)]
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
                with ttl_file_path.open("w+") as ttl_file:
                    # args = −f ’xmlns:prefix="uri"’
                    check_call(args, stdout=ttl_file)
                inputs[nt_file_path.stem]["Turtle"] = ttl_file_path

    compressors_by_name_ = compressors_by_name()
    rdf_formats = tuple(sorted(set(rdf_format for dict_ in inputs.values() for rdf_format in dict_)))

    with (root_directory_path / "results.csv").open("w+") as results_csv_file:
        csv_fieldnames = ["Input"]
        for rdf_format in rdf_formats:
            csv_fieldnames.append(f"{rdf_format} bytes")
            csv_fieldnames.append(f"{rdf_format} human")
            for compressor_name in compressors_by_name_:
                csv_fieldnames.append(f"{rdf_format} {compressor_name} bytes")
                csv_fieldnames.append(f"{rdf_format} {compressor_name} human")
                csv_fieldnames.append(f"{rdf_format} {compressor_name} compression ratio")
                csv_fieldnames.append(f"{rdf_format} {compressor_name} space savings")
        csv_writer = csv.DictWriter(results_csv_file, fieldnames=csv_fieldnames)
        csv_writer.writeheader()
        for input_name in inputs.keys():
            csv_row = {"Input": input_name}
            for rdf_format, input_file_path in inputs[input_name].items():
                uncompressed_size = stat(input_file_path).st_size
                csv_row[f"{rdf_format} bytes"] = str(uncompressed_size)
                csv_row[f"{rdf_format} human"] = sizeof_fmt(uncompressed_size)
                for compressor_name, compressor in compressors_by_name_.items():
                    print("compressing", input_file_path, "with", compressor_name)
                    output_file_path = compressor(input_file_path, output_directory_path)
                    compressed_size = stat(output_file_path).st_size
                    print("compressed", input_file_path, "with", compressor_name, "to", output_file_path, ":", compressed_size , "bytes")
                    csv_row[f"{rdf_format} {compressor_name} bytes"] = str(compressed_size)
                    csv_row[f"{rdf_format} {compressor_name} human"] = sizeof_fmt(compressed_size)
                    csv_row[f"{rdf_format} {compressor_name} compression ratio"] = f"{uncompressed_size / compressed_size:.2f}"
                    csv_row[f"{rdf_format} {compressor_name} space savings"] = f"{1 - (compressed_size / uncompressed_size):.2f}"

            csv_writer.writerow(csv_row)


if __name__ == "__main__":
    main()