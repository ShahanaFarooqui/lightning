import os
import json

# Input folder containing JSON files
input_folder = "/home/shahana/workspace/lightning/doc/"

raw_request_date = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "additionalProperties": False,
    "required": [],
    "properties": {}
}

# Process all files in the input folder
for root, _, files in os.walk(os.path.join(input_folder, "schemas")):
    # Group request and schema files with the same name
    grouped_files = []
    for file in files:
        if file.endswith(".schema.json"):
            base_name = file[:-12]
            if base_name not in grouped_files:
                grouped_files.append(base_name)

# grouped_files = ["commando-listrunes"]

# Merge and create new JSON files
for base_name in grouped_files:
    if not os.path.exists(input_folder + "lightning-" + base_name + ".7.md"):
        print("MD not found for " + base_name)
        continue
    elif not os.path.exists(input_folder + "schemas/" + base_name + ".schema.json"):
        print("SCHEMA not found for " + base_name)
        continue
    elif not os.path.exists(input_folder + "schemas/" + base_name + ".request.json"):
        with open(input_folder + "schemas/" + base_name + ".request.json", "w") as request_file:
            json.dump("", request_file, indent=2)
            # json.dump(raw_request_date, request_file, indent=2)
            print("REQUEST created for " + base_name)

    with open(input_folder + "schemas/" + base_name + ".request.json", "r") as request_file, \
            open(input_folder + "schemas/" + base_name + ".schema.json", "r") as response_file, \
            open(input_folder + "lightning-" + base_name + ".7.md", "r") as md_file:
        print(f"Merging base file: {base_name}")
        request_json = json.load(request_file)
        response_json = json.load(response_file)
        merged_json = {}
        merged_json["$schema"] = request_json.get("$schema", "http://json-schema.org/draft-07/schema#")
        merged_json["type"] = request_json.get("type", "object")
        merged_json["additionalProperties"] = request_json.get("additionalProperties", False)
        for key in ["$schema", "type", "additionalProperties"]:
            request_json.pop(key, None)
            response_json.pop(key, None)
        if "added" in request_json:
            merged_json["added"] = request_json["added"]
            request_json.pop("added", None)
        if "deprecated" in request_json:
            merged_json["deprecated"] = request_json["deprecated"]
            request_json.pop("deprecated", None)
        if base_name == "stop":
            response_json["type"] = "string"
        md_file_contents = [line.strip("\n") for line in md_file.readlines()]
        for i in range(0, len(md_file_contents)):
            line = md_file_contents[i]
            if i == 0:
                line = line.removeprefix("lightning-")
                rpc, title = line.split(" -- ")
                merged_json["rpc"] = rpc.strip()
                merged_json["title"] = title.strip("\n")
            else:
                title_line = md_file_contents[i - 1].strip("\n")
                if line.startswith("----") and not (title_line.startswith("SYNOPSIS")):
                    for j in range(i+2, len(md_file_contents)):
                        if md_file_contents[j].startswith("----"):
                            title_line_end = j - 2
                            break
                    if title_line.startswith("RETURN VALUE"):
                        for j in range(i+2, len(md_file_contents)):
                            if md_file_contents[j].startswith("[comment]: # (GENERATE-FROM-SCHEMA-START)"):
                                pre_notes_end = j - 1
                                break
                        pre_return_value_notes = md_file_contents[i+2:pre_notes_end]
                        for k in range(j, len(md_file_contents)):
                            if md_file_contents[k].startswith("[comment]: # (GENERATE-FROM-SCHEMA-END)"):
                                post_notes_start = k + 2
                            if md_file_contents[k].startswith("----"):
                                post_notes_end = k - 2
                                break
                        post_return_value_notes = md_file_contents[post_notes_start:post_notes_end]
                        if len(pre_return_value_notes) > 0:
                            response_json["pre_return_value_notes"] = pre_return_value_notes
                        if len(post_return_value_notes) > 0:
                            response_json["post_return_value_notes"] = post_return_value_notes
                    elif title_line.startswith("DESCRIPTION") or title_line.startswith("EXAMPLE JSON REQUEST"):
                        request_json[title_line.lower().replace(" ", "_")] = md_file_contents[i+2:title_line_end]
                        merged_json["request"] = request_json
                        merged_json["response"] = response_json
                    elif title_line.startswith("SEE ALSO"):
                        merged_json["see_also"] = "".join(md_file_contents[i+2:title_line_end]).strip(".").split(", ")
                    elif title_line.startswith("RESOURCES"):
                        for j in range(i+2, len(md_file_contents)):
                            if md_file_contents[j].startswith("[comment]: # ( SHA256STAMP:"):
                                title_line_end = j - 1
                                break
                        merged_json[title_line.lower()] = md_file_contents[i+2:title_line_end]
                    else:
                        merged_json[title_line.lower().replace(" ", "_")] = md_file_contents[i+2:title_line_end]
                    i = j
    # Write merged JSON to the new file
    output_file = os.path.join(input_folder, "schemas", f"lightning-{base_name}.json")
    with open(output_file, "w") as outfile:
        json.dump(merged_json, outfile, indent=2)
