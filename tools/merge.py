import os
import json

# Input folder containing JSON files
input_folder = "/home/shahana/workspace/lightning/doc/"
# Process all files in the input folder
for root, _, files in os.walk(os.path.join(input_folder, "schemas")):
    # Group request and schema files with the same name
    grouped_files = []
    for file in files:
        if file.endswith(".schema.json"):
            base_name = file[:-12]
            if base_name not in grouped_files:
                grouped_files.append(base_name)

# Merge and create new JSON files
for base_name in grouped_files:
    if os.path.exists(input_folder + "schemas/" + base_name + ".request.json") \
    and os.path.exists(input_folder + "schemas/" + base_name + ".schema.json") \
    and os.path.exists(input_folder + "lightning-" + base_name + ".7.md"):
        with open(input_folder + "schemas/" + base_name + ".request.json", "r") as request_file, \
             open(input_folder + "schemas/" + base_name + ".schema.json", "r") as response_file, \
             open(input_folder + "lightning-" + base_name + ".7.md", "r") as md_file:
            request_json = json.load(request_file)
            response_json = json.load(response_file)
            merged_json = {}
            merged_json["$schema"] = request_json.get("$schema", "http://json-schema.org/draft-07/schema#")
            merged_json["type"] = request_json.get("type", "object")
            merged_json["additionalProperties"] = request_json.get("additionalProperties", False)
            request_json.pop("$schema", None)
            request_json.pop("type", None)
            request_json.pop("additionalProperties", None)
            if "added" in request_json:
                merged_json["added"] = request_json["added"]
                request_json.pop("added", None)
            if "deprecated" in request_json:
                merged_json["deprecated"] = request_json["deprecated"]
                request_json.pop("deprecated", None)
            description_line_s = 0
            description_line_e = 0
            author_line_s = 0
            author_line_e = 0
            see_also_line_s = 0
            see_also_line_e = 0
            md_file_contents = md_file.readlines()
            for i, line in enumerate(md_file_contents):
                if i == 0:
                    line = line.removeprefix("lightning-")
                    rpc, title = line.split(" -- ")
                    merged_json["rpc"] = rpc.strip()
                    merged_json["title"] = title.strip("\n")
                if line.startswith("DESCRIPTION"):
                    description_line_s = i + 3
                if line.startswith("RETURN VALUE"):
                    description_line_e = i - 1
                if line.startswith("AUTHOR"):
                    author_line_s = i + 3
                if line.startswith("SEE ALSO"):
                    see_also_line_s = i + 3
                    author_line_e = i - 1
                if line.startswith("RESOURCES"):
                    see_also_line_e = i - 1
            md_file_contents[description_line_e - 1] = md_file_contents[description_line_e - 1].strip("\n")
            md_file_contents[author_line_e - 1] = md_file_contents[author_line_e - 1].strip("\n")

            description = md_file_contents[description_line_s:description_line_e]
            authors = md_file_contents[author_line_s:author_line_e]
            see_also = "".join(md_file_contents[see_also_line_s:see_also_line_e]).replace("\n", "").replace(" ", "").split(",")

            request_json["description"] = description
            merged_json["authors"] = authors
            merged_json["seeAlso"] = see_also

            response_json.pop("$schema", None)
            response_json.pop("type", None)
            response_json.pop("additionalProperties", None)

            merged_json["request"] = request_json
            merged_json["response"] = response_json
        # Write merged JSON to the new file
        output_file = os.path.join(input_folder, "schemas", f"{base_name}.new.json")
        with open(output_file, "w") as outfile:
            json.dump(merged_json, outfile, indent=2)
    else:
        print(base_name, "not found")
