# def get_matched_property_keys(schema_json):

#     search_dict = schema_json
#     target_dict = schema_json

#     inverted_index = defaultdict(list)
#     for t_key, words in target_dict.items():
#         for word in words:
#             inverted_index[word].append(t_key)

#     result_dict = {}
#     for s_key, search_words in search_dict.items():
#         result_dict[s_key] = defaultdict(list)
#         s_db = None if s_key.isupper() else s_key.split("_")[0]
#         for word in search_words:
#             if word in inverted_index:
#                 for t_key in inverted_index[word]:
#                     if t_key == s_key: continue
#                     t_db = None if t_key.isupper() else t_key.split("_")[0]
#                     if s_db == t_db: continue
#                     result_dict[s_key][t_key].append(word)

#     for s_key in result_dict:
#         result_dict[s_key] = dict(result_dict[s_key])

#     return result_dict
# with open("step_1_1_concept_expansion/possible_concept_labels.json", "r") as f:
#     possible_concept_labels = json.load(f).keys()
#     schema_json = extract_json()
#     
#     schema_json = {k: list(filter(lambda x: x not in generic_property_keys, v)) for k, v in schema_json.items()}
#     matched_property_keys = get_matched_property_keys(schema_json)   
#     print(json.dumps(matched_property_keys, indent=4))