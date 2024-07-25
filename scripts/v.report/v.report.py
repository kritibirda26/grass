#!/usr/bin/env python3
#
############################################################################
#
# MODULE:       v.report
# AUTHOR(S):    Markus Neteler, converted to Python by Glynn Clements
#               Bug fixes, sort for coor by Huidae Cho <grass4u gmail.com>
# PURPOSE:      Reports geometry statistics for vector maps
# COPYRIGHT:    (C) 2005-2021 by MN and the GRASS Development Team
#
#               This program is free software under the GNU General Public
#               License (>=v2). Read the file COPYING that comes with GRASS
#               for details.
#
#############################################################################

# %module
# % description: Reports geometry statistics for vector maps.
# % keyword: vector
# % keyword: geometry
# % keyword: statistics
# %end
# %option G_OPT_V_MAP
# %end
# %option G_OPT_V_FIELD
# % guisection: Selection
# %end
# %option
# % key: option
# % type: string
# % description: Value to calculate
# % options: area,length,coor
# % required: yes
# %end
# %option G_OPT_M_UNITS
# % options: miles,feet,meters,kilometers,acres,hectares,percent
# %end
# %option
# % key: sort
# % type: string
# % description: Sort the result
# % options: asc,desc
# % descriptions: asc;Sort in ascending order;desc;Sort in descending order
# %end
# %option G_OPT_F_SEP
# %end
# %option G_OPT_F_FORMAT
# % key: format
# % type: string
# % key_desc: name
# % required: yes
# % label: Output Format
# % answer: plain
# % options: plain,json
# % descriptions: plain;Plain text output;json;JSON (JavaScript Object Notation);
# % guisection: Print
# %end
# %flag
# % key: c
# % description: Do not include column names in output
# %end
# %flag
# % key: d
# % description: Report for geometries with no database records
# %end

import sys
import json
import grass.script as gs
from grass.script.utils import separator, decode


def uniq(items):
    result = []
    last = None
    for i in items:
        if i != last:
            result.append(i)
            last = i
    return result


def main():
    mapname = options["map"]
    layer = options["layer"]
    option = options["option"]
    units = options["units"]
    sort = options["sort"]
    fs = separator(options["separator"])
    output_format = options["format"]

    if not gs.find_file(mapname, "vector")["file"]:
        gs.fatal(_("Vector map <%s> not found") % mapname)

    if option == "coor":
        extracolnames = ["x", "y", "z"]
    else:
        extracolnames = [option]

    if units == "percent":
        unitsp = "meters"
    elif units:
        unitsp = units
    else:
        unitsp = None

    vdb = gs.vector_db(mapname)
    # NOTE: we suppress -1 cat and 0 cat
    if int(layer) in vdb:
        f = vdb[int(layer)]
        catcol_name = f["key"]
        p = gs.pipe_command(
            "v.db.select", quiet=True, map=mapname, layer=layer, format="json"
        )
        db_output = json.loads(p.stdout.read())
        columns = db_output["info"]["columns"]
        colnames = [c["name"] for c in columns]

        records1 = db_output["records"]

        if catcol_name not in colnames:
            gs.fatal(
                _(
                    "There is a table connected to input vector map '%s', but "
                    "there is no key column '%s'."
                )
                % (mapname, f["key"])
            )

        p.wait()
        if p.returncode != 0:
            sys.exit(1)

        records1.sort(key=lambda r1: r1[catcol_name])

        if len(records1) == 0:
            gs.fatal(
                _(
                    "There is a table connected to input vector map '%s', but "
                    "there are no categories present in the key column '%s'. "
                    "Consider using v.to.db to correct this."
                )
                % (mapname, catcol_name)
            )

        # fetch the requested attribute sorted by cat:
        p = gs.pipe_command(
            "v.to.db",
            flags="p",
            quiet=True,
            map=mapname,
            option=option,
            layer=layer,
            units=unitsp,
        )

        records2 = []
        for line in p.stdout:
            fields = decode(line).rstrip("\r\n").split("|")
            if fields[0] in {"cat", "-1", "0"}:
                continue
            fields[0] = int(fields[0])
            records2.append(fields)
        p.wait()
        records2.sort()

        ncols = len(colnames)
        # make pre-table
        # len(records1) may not be the same as len(records2) because
        # v.db.select can return attributes that are not linked to features.
        records3 = []
        for r2 in records2:
            rec = list(filter(lambda r1: r1[catcol_name] == r2[0], records1))
            if len(rec) > 0:
                rec[0][option] = r2[1:]
                records3.append(rec[0])
            elif flags["d"]:  # fixme
                res = [r2[0]] + [""] * (ncols - 1) + r2[1:]
                records3.append(res)
            else:
                continue
    else:
        colnames = ["cat"]
        records1 = []
        p = gs.pipe_command("v.category", inp=mapname, layer=layer, option="print")
        for line in p.stdout:
            field = int(decode(line).rstrip())
            if field > 0:
                records1.append(field)
        p.wait()
        records1.sort()
        records1 = uniq(records1)

        # make pre-table
        p = gs.pipe_command(
            "v.to.db",
            flags="p",
            quiet=True,
            map=mapname,
            option=option,
            layer=layer,
            units=unitsp,
        )
        records3 = []
        for line in p.stdout:
            fields = decode(line).rstrip("\r\n").split("|")
            if fields[0] in {"cat", "-1", "0"}:
                continue
            fields[0] = int(fields[0])
            records3.append(fields)
        p.wait()
        records3.sort()

    # print table header
    if not flags["c"] and output_format != "json":
        sys.stdout.write(fs.join(colnames + extracolnames) + "\n")

    # calculate percents if requested
    if units == "percent" and option != "coor":
        # calculate total value
        total = 0
        for r in records3:
            total += float(r[-1])

        # calculate percentages
        records4 = [float(r[-1]) * 100 / total for r in records3]
        if type(records1[0]) == int:
            records3 = [[r1] + [r4] for r1, r4 in zip(records1, records4)]
        else:
            records3 = [r1 + [r4] for r1, r4 in zip(records1, records4)]

    # sort results
    if sort:
        if option == "coor":
            records3.sort(
                key=lambda r: (float(r[-3]), float(r[-2]), float(r[-1])),
                reverse=(sort != "asc"),
            )
        else:
            records3.sort(key=lambda r: float(r[-1]), reverse=(sort != "asc"))

    if output_format != "json":
        for r in records3:
            sys.stdout.write(fs.join(map(str, r.values())) + "\n")
    else:
        all_cols = []
        all_cols.extend(colnames)
        all_cols.extend(extracolnames)

        data = []
        for r in records3:
            item = {key: value for key, value in zip(all_cols, r)}
            data.append(item)
        sys.stdout.write(json.dumps(data, indent=4) + "\n")


if __name__ == "__main__":
    options, flags = gs.parser()
    main()
