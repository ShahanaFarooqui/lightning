#! /usr/bin/env python3
# Script to turn JSON schema into markdown documentation and replace in-place.
# Released by Rusty Russell under CC0:
# https://creativecommons.org/publicdomain/zero/1.0/
from argparse import ArgumentParser
import json
import re

def output_title(title, underline="-", num_leading_newlines=1, num_trailing_newlines=2):
    """Add a title to the output"""
    print("\n" * num_leading_newlines + title, end="\n")
    print(underline * len(title) + "\n" * num_trailing_newlines, end="")


def esc_underscores(s):
    """Backslash-escape underscores outside of backtick-enclosed spans"""
    return "".join(["\\_" if x == "_" else x for x in re.findall(r"[^`_\\]+|`(?:[^`\\]|\\.)*`|\\.|_", s)])


def json_value(obj):
    """Format obj in the JSON style for a value"""
    if type(obj) is bool:
        if obj:
            return "*true*"
        return "*false*"
    if type(obj) is str:
        return '"' + esc_underscores(obj) + '"'
    if obj is None:
        return "*null*"
    assert False


def outputs(lines, separator=""):
    """Add these lines to the final output"""
    print(separator.join(lines), end="")


def output(line):
    """Add this line to the final output"""
    print(line, end='')


def output_type(properties, is_optional):
    if "oneOf" in properties:
        properties["type"] = "one of"
    typename = esc_underscores(properties["type"])
    if typename == "array":
        if "items" in properties and "type" in properties["items"]:
            typename += " of {}s".format(esc_underscores(properties["items"]["type"]))
    if is_optional:
        typename += ", optional"
    output(" ({}):".format(typename) if "description" in properties and properties["description"] != "" else " ({})".format(typename))


def output_range(properties, brackets=True):
    if "maximum" and "minimum" in properties:
        output(" ({} to {} inclusive)".format(properties["minimum"],
                                              properties["maximum"]))
    elif "maximum" in properties:
        output(" (max {})".format(properties["maximum"]))
    elif "minimum" in properties:
        output(" (min {})".format(properties["minimum"]))

    if "maxLength" and "minLength" in properties:
        if properties["minLength"] == properties["maxLength"]:
            if brackets is True:
                output(" (always {} characters)".format(properties["minLength"]))
            else:
                output("always {} characters".format(properties["minLength"]))
        else:
            if brackets is True:
                output(" ({} to {} characters)".format(properties["minLength"], properties["maxLength"]))
            else:
                output("{} to {} characters".format(properties["minLength"], properties["maxLength"]))
    elif "maxLength" in properties:
        if brackets is True:
            output(" (up to {} characters)".format(properties["maxLength"]))
        else:
            output("up to {} characters".format(properties["maxLength"]))
    elif "minLength" in properties:
        if brackets is True:
            output(" (at least {} characters)".format(properties["minLength"]))
        else:
            output("at least {} characters".format(properties["minLength"]))

    if "enum" in properties:
        if len(properties["enum"]) == 1:
            if brackets is True:
                output(" (always {})".format(json_value(properties["enum"][0])))
            else:
                output("always {}".format(json_value(properties["enum"][0])))
        else:
            if brackets is True:
                output(" (one of {})".format(", ".join([json_value(p) for p in properties["enum"]])))
            else:
                output("one of {}".format(", ".join([json_value(p) for p in properties["enum"]])))

    if list(properties.keys()) == ["type"] and properties["type"] == "string":
        output("(" + properties["type"] + ")")


def fmt_propname(propname):
    """Pretty-print format a property name"""
    return "**{}**".format(esc_underscores(propname))


def deprecated_to_deleted(vername):
    """We promise a 6 month minumum deprecation period, and versions are every 3 months"""
    assert vername.startswith("v")
    base = [int(s) for s in vername[1:].split(".")[0:2]]
    if base == [0, 12]:
        base = [22, 8]
    base[1] += 9
    if base[1] > 12:
        base[0] += 1
        base[1] -= 12
    # Christian points out versions should sort well lexographically,
    # so we zero-pad single-digits.
    return "v{}.{:0>2}".format(base[0], base[1])


def output_member(propname, properties, is_optional, indent, print_type=True, prefix=None):
    """Generate description line(s) for this member"""

    if prefix is None:
        prefix = "- " + fmt_propname(propname) if propname is not None else "- "
    output(indent + prefix)

    # We make them explicitly note if they don"t want a type!
    is_untyped = "untyped" in properties

    if not is_untyped and print_type:
        output_type(properties, is_optional)

    if "description" in properties:
        output(" {}".format(esc_underscores(properties["description"])))

    output_range(properties)

    if "deprecated" in properties:
        output(" **deprecated, removal in {}**".format(deprecated_to_deleted(properties["deprecated"])))
    if "added" in properties:
        output(" *(added {})*".format(properties["added"]))

    output("\n")
    if "oneOf" in properties and isinstance(properties["oneOf"], list):
        output_members(properties, indent + "  ")
    elif not is_untyped and properties["type"] == "object":
        output_members(properties, indent + "  ")
    elif not is_untyped and properties["type"] == "array":
        output_array(properties["items"], indent + "  ")


def output_array(items, indent):
    """We"ve already said it"s an array of {type}"""
    if "oneOf" in items and isinstance(items["oneOf"], list):
        output_members(items, indent + "  ")
    elif list(items.keys()) == ["type"]:
        output(indent + "- " + items["type"] + "\n")
    elif items["type"] == "object":
        output_members(items, indent)
    elif items["type"] == "array":
        output(indent + "-")
        output_type(items, False)
        output(" {}\n".format(esc_underscores(items["description"])) if "description" in items and items["description"] != "" else "\n")
        if "items" in items: 
            output_array(items["items"], indent + "  ")
    else:
        if "description" in items and items["description"] != "": 
            output(indent + "-")
            output(" {}".format(esc_underscores(items["description"])))
        output_range(items)
        output("\n")


def has_members(sub):
    """Does this sub have any properties to print?"""
    for p in list(sub["properties"].keys()):
        if len(sub["properties"][p]) == 0:
            continue
        if sub["properties"][p].get("deprecated") is True:
            continue
        return True
    return False


def output_members(sub, indent=""):
    """Generate lines for these properties"""
    warnings = []
    # Remove deprecated: True and stub properties, collect warnings
    # (Stubs required to keep additionalProperties: false happy)

    # FIXME: It fails for schemas which have only an array type with
    # no properties, ex:
    # "abcd": {
    #  "type": "array",
    #   "items": {
    #    "type": "whatever",
    #    "description": "efgh"
    #   }
    # }
    # Checkout the schema of `staticbackup`.
    if "properties" in sub:
        for p in list(sub["properties"].keys()):
            if len(sub["properties"][p]) == 0 or sub["properties"][p].get("deprecated") is True:
                del sub["properties"][p]
            elif p.startswith("warning"):
                warnings.append(p)

        # First list always-present properties
        for p in sub["properties"]:
            if p.startswith("warning"):
                continue
            if "required" in sub and p in sub["required"]:
                output_member(p, sub["properties"][p], False, indent)

        for p in sub["properties"]:
            if p.startswith("warning"):
                continue
            if "required" not in sub or p not in sub["required"]:
                output_member(p, sub["properties"][p], True, indent)

    if warnings != []:
        output(indent + "- the following warnings are possible:\n")
        for w in warnings:
            output_member(w, sub["properties"][w], False, indent + "  ", print_type=False)

    if "oneOf" in sub:
        for oneOfItem in sub["oneOf"]:
            if "type" in oneOfItem and oneOfItem["type"] == "object":
                output_member(None, oneOfItem, False, indent, "-")
            elif "type" in oneOfItem and oneOfItem["type"] == "array":
                output_array(oneOfItem, indent)
            elif "type" in oneOfItem and oneOfItem["type"] == "string":
                output(indent + "- ")
                output_range(oneOfItem, False)
                output("\n")

    # If we have multiple ifs, we have to wrap them in allOf.
    if "allOf" in sub:
        ifclauses = sub["allOf"]
    elif "if" in sub:
        ifclauses = [sub]
    else:
        ifclauses = []

    # We partially handle if, assuming it depends on particular values of prior properties.
    for ifclause in ifclauses:
        conditions = []

        # "required" are fields that simply must be present
        for r in ifclause["if"].get("required", []):
            conditions.append(fmt_propname(r) + " is present")

        # "properties" are enums of field values
        for tag, vals in ifclause["if"].get("properties", {}).items():
            # Don"t have a description field here, it"s not used.
            assert "description" not in vals
            whichvalues = vals["enum"]

            cond = fmt_propname(tag) + " is"
            if len(whichvalues) == 1:
                cond += " {}".format(json_value(whichvalues[0]))
            else:
                cond += " {} or {}".format(", ".join([json_value(v) for v in whichvalues[:-1]]),
                                        json_value(whichvalues[-1]))
            conditions.append(cond)

        sentence = indent + "If " + ", and ".join(conditions) + ":\n"

        if has_members(ifclause["then"]):
            # Prefix with blank line.
            outputs(["\n", sentence])
            output_members(ifclause["then"], indent + "  ")
            output("\n")


def output_params(schema):
    request = schema["request"]
    toplevels = list(request["properties"].keys())

    output("{}".format(fmt_propname(schema["rpc"])))
    for p in toplevels:
        if "required" in request and p in request["required"]:
            output(" *" + p + "*")
        else:
            output(" [*" + p + "*]")
    output("\n")


def generate_from_response(schema):
    """This is not general, but works for us"""
    output_title("RETURN VALUE")
    
    response = schema["response"]

    if "pre_return_value_notes" in response:
        outputs(response["pre_return_value_notes"], "\n")
        output("\n\n")

    if "properties" not in response and "enum" in response:
        # "stop" returns a single enum string and post_return_value_notes!
        output_member(None, response, False, "", prefix="On success, returns a single element")
        output("\n")
        if "post_return_value_notes" in response:
            outputs(response["post_return_value_notes"], "\n")
        return

    toplevels = []
    warnings = []
    props = response["properties"]
    
    # We handle warnings on top-level objects with a separate section,
    # so collect them now and remove them
    for toplevel in list(props.keys()):
        if toplevel.startswith("warning"):
            warnings.append((toplevel, props[toplevel]["description"]))
            del props[toplevel]
        else:
            toplevels.append(toplevel)

    # No properties -> empty object.
    if toplevels == []:
        output("On success, an empty object is returned.\n")
        sub = schema
    elif len(toplevels) == 1 and props[toplevels[0]]["type"] == "object":
        output("On success, an object containing {} is returned.  It is an object containing:\n\n".format(fmt_propname(toplevels[0])))
        # Don"t have a description field here, it"s not used.
        assert "description" not in toplevels[0]
        sub = props[toplevels[0]]
    elif len(toplevels) == 1 and props[toplevels[0]]["type"] == "array" and props[toplevels[0]]["items"]["type"] == "object":
        output("On success, an object containing {} is returned.  It is an array of objects, where each object contains:\n\n".format(fmt_propname(toplevels[0])))
        # Don"t have a description field here, it"s not used.
        assert "description" not in toplevels[0]
        sub = props[toplevels[0]]["items"]
    else:
        output("On success, an object is returned, containing:\n\n")
        sub = response

    output_members(sub)

    if warnings:
        outputs(["\n", "The following warnings may also be returned:\n\n"])
        for w, desc in warnings:
            output("- {}: {}\n".format(fmt_propname(w), desc))
        output("\n")

    if "post_return_value_notes" in response:
        output("\n")
        outputs(response["post_return_value_notes"], "\n")
        output("\n")


def generate_header(schema):
    output_title("".join(["lightning-", schema["rpc"], " -- ", schema["title"]]), "=", 0, 1)
    output_title("SYNOPSIS")
    output_params(schema)


def generate_from_request(schema):
    request = schema["request"]
    request_key_list = [key for key in list(request.keys()) if key not in ['required', 'properties']]
    props = request["properties"]
    toplevels = list(props.keys())
    indent=""

    for key in request_key_list:
        output_title(key.replace("_", " ").upper())
        if key == "description":
            if "deprecated" in schema:
                output("Command **deprecated, removal in {}**.\n\n".format(deprecated_to_deleted(schema["deprecated"])))
            if "added" in schema:
                output("Command *added* in {}.\n\n".format(schema["added"]))
            outputs(request[key], "\n")
            if len(props) > 0:
                output("\n\n")
                if toplevels == []:
                    sub = schema["request"]
                elif len(toplevels) == 1 and "oneOf" in props[toplevels[0]] and isinstance(props[toplevels[0]]["oneOf"], list):
                    output("{}".format(fmt_propname(toplevels[0])))
                    output_type(props[toplevels[0]], False if toplevels[0] in schema["request"]["required"] else True)
                    output("\n")
                    indent = indent + "  "
                    sub = props[toplevels[0]]
                elif len(toplevels) == 1 and props[toplevels[0]]["type"] == "object":
                    output("{}\n".format(fmt_propname(toplevels[0])))
                    assert "description" not in toplevels[0]
                    sub = props[toplevels[0]]
                elif len(toplevels) == 1 and props[toplevels[0]]["type"] == "array" and props[toplevels[0]]["items"]["type"] == "object":
                    output("{}\n".format(fmt_propname(toplevels[0])))
                    assert "description" not in toplevels[0]
                    sub = props[toplevels[0]]["items"]
                else:
                    sub = schema["request"]
                output_members(sub, indent)
            else:
                output("\n")
        else:
            outputs(request[key], "\n")


def generate_footer(schema):
    keys = list(schema.keys())
    footer_key_list = [key for key in keys if key not in ['$schema', 'type', 'additionalProperties', 'rpc', 'title', 'request', 'response', 'added', 'deprecated']]
    for i, key in enumerate(footer_key_list):
        output_title(key.replace("_", " ").upper(), "-", 1 if i == 0 else 2)
        outputs(schema[key], ", " if key in ['categories', 'see_also'] else "\n")
    output("\n\n")


def main(schemafile, markdownfile):
    with open(schemafile, "r") as f:
        schema = json.load(f)
    generate_header(schema)
    generate_from_request(schema)
    generate_from_response(schema)
    generate_footer(schema)

    if markdownfile is None:
        return


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("schemafile", help="The schema file to use")
    parser.add_argument("--markdownfile", help="The markdown file to read")
    parsed_args = parser.parse_args()
    main(parsed_args.schemafile, parsed_args.markdownfile)
