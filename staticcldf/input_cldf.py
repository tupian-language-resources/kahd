# Import MPI-SHH libraries
from pycldf.dataset import Dataset


def read_cldf_data(config):
    """
    Read CLDF data as lists of Python dictionaries.

    This function interfaces with `pycldf`. The tables and columns to
    extract are obtained from `*_fields` entries in `config`.

    Parameters
    ----------
    config : dict
        A dictionary with the configurations.
    """

    # Read dataset from metadata
    metadata = config["base_path"] / "demo_cldf" / "cldf-metadata.json"
    dataset = Dataset.from_metadata(metadata.as_posix())

    # Transform the dataset in a Python datastructure (`cldf_data`) suitable
    # for Jinja template manipulation. `cldf_data` is a dictionary of
    # tables, where the key is the table_name and value is a dictionary
    # of `columns` (with the sorted list of column names, found in the
    # rows), and `rows`. `rows` is a list of dictionaries, with the
    # `value` to be reported and optionally other information (such as the
    # `url`) which may or may not be used by the template
    # (`value` is always used).
    # TODO: make conversion less explicit and with fewer loops
    # table.base -> /home/tresoldi/src/staticcldf/demo_cldf
    # table.url -> cognates.csv
    # table.local_name -> cognates.csv
    # for col in table.tableSchema.columns:
    #   - col.datatype.base -> string, decimal
    #   - col.header -> Alignment_Source
    #   - col.name -> Alignment_Source
    #   - col.propertyUrl -> None, http://cldf.clld.org/v1.0/terms.rdf#alignment
    #   - col.valueUrl -> None, http://glottolog.org/resource/languoid/id/{glottolog_id}
    cldf_data = {}
    for table in dataset.tables:
        table_key = table.local_name.split(".")[0]

        column_names = [col.name for col in table.tableSchema.columns]
        valueUrls = [col.valueUrl for col in table.tableSchema.columns]
        datatypes = [col.datatype.base for col in table.tableSchema.columns]

        # Holder for the table values in the returned structure
        table_data = []

        # Iterate over all rows for the current table
        for row in table:
            # Holder for the row in the returned structure
            row_data = []

            # Iterate over all columns for the current row
            for column, valueUrl in zip(column_names, valueUrls):
                if not row[column]:
                    value = ""
                elif isinstance(row[column], (list, tuple)):
                    value = " ".join([str(value) for value in row[column]])
                else:
                    value = str(row[column])

                if valueUrl:
                    # Ugly replacement, but works with CLDF metadata
                    # (assuming there is a single replacement)
                    var_name = list(valueUrl.variable_names)[0]
                    url = valueUrl.expand(**{var_name: value})
                else:
                    url = None

                # Append computed values to `row_data`
                row_data.append({"value": value, "url": url})

            # Append current row to the table
            table_data.append(row_data)

        #  Append contents to overall table
        column_data = [
            {"name": name, "datatype": datatype}
            for name, datatype in zip(column_names, datatypes)
        ]
        cldf_data[table_key] = {"columns": column_data, "rows": table_data}

    # TODO: remove those which are all empty or None

    return cldf_data
