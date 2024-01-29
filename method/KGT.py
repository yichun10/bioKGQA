import networkx as nx  
from transformers import AutoTokenizer
import transformers
import torch
from tqdm import tqdm
import json
import re
from transformers import AutoModel, AutoTokenizer, pipeline
from py2neo import Node, Graph, Relationship,NodeMatcher
from transformers import BertTokenizer, BertModel
import pandas as pd
from scipy.spatial.distance import cosine
dataset = []
"""
{
    "question":,
    "answer":
}
"""
link1 = Graph("address", auth=("neo4j", "key"))# KG information

model1 = "" #model route
tokenizer = AutoTokenizer.from_pretrained(model1)
pipeline1 = transformers.pipeline(
    "text-generation",
    model=model1,
    torch_dtype=torch.float16,
    device_map="auto", 
)

model1 = AutoModel.from_pretrained(model1)

def get_sentence_embedding(sentence, model, tokenizer):
    inputs = tokenizer(sentence, return_tensors="pt")
    outputs = model(**inputs)
    return outputs.last_hidden_state.mean(dim=1)

def calculate_similarity(sentence1, sentence2, model, tokenizer):
    embedding1 = get_sentence_embedding(sentence1, model, tokenizer)
    embedding2 = get_sentence_embedding(sentence2, model, tokenizer)
    similarity = 1 - cosine(embedding1.squeeze(0).detach().numpy(), embedding2.squeeze(0).detach().numpy())
    return similarity
def exception_(old_question):
    prompt = """
    You are a reasoning robot, and you need to output natural language to answer my questions.
    For example:

    """
    input_text1 = prompt +old_question
    sequences = pipeline1(
        input_text1,
        do_sample=True,
        top_k=10,
        return_full_text=False,
        top_p = 0.7,  
        temperature = 0.8, 
        num_return_sequences=1,
        eos_token_id=tokenizer.eos_token_id,
        max_length=2000, 
    )
    for seq in sequences:
        lines = seq['generated_text'].split('\n')
        for line in lines:
            if line.strip(): 
                out=line
                break  
    dataset.append(
        {
        "question":old_question,
        "answer": out
        }
    )

# Read JSON file
file_path = ''  # Replace with your test JSON file path
with open(file_path, 'r', encoding='utf-8') as file:
    data = json.load(file)
for item in tqdm(data):
    try:
        old_question = item['question']
        gxl_pro=""
        first_pro=""
        third_element=""
        first_element=""
        second_element=""
        name_ht=""
        name_pro=""
        target1=""
        first_name=""

        #Extract Key Information
        prompt = """
        You need to follow these three steps based on your biomedical knowledge:
        step1:Extract the name of the head entity and the type of the tail entity in my question,with the head defined as the active voice of the problem and the tail defined as the passive voice of the problem. The entity types include: Drug, Genesymbol... 
        step2:Based on the entity type from step 1, select an attribute from the attribute list that best fits my question.
        step3:If there is only one head entity name, the output format should be(head entity name, tail entity type, attribute); if there are two head entity names, the output format should be(head entity name 1,tail entity type, attribute),(head entity name 2,tail entity type, attribute).
        
        The attribute list is:
        "Drug": "drug.id, drug.name...
        For example:

        """
        input_text1 = prompt + old_question
        sequences = pipeline1(
            input_text1,
            do_sample=True,
            top_k=10,
            return_full_text=False,
            top_p = 0.95,  
            temperature = 0.01, 
            num_return_sequences=1,
            eos_token_id=tokenizer.eos_token_id,
            max_length=2000, 
        )
        for seq in sequences:
            lines = seq['generated_text'].split('\n')
            for line in lines:
                if line.strip(): 
                    break 
        count = line.count('(')
        if 'relation' in old_question:
            target1 = "Relationship detected"
        if count == 1:
            first_element = line.split(',')[0].strip('() ')
            second_cypher_query=f"""
            MATCH (e) 
            WHERE e.name_en = '{first_element}'
            RETURN e.name
            """
            name_ans=link1.run(second_cypher_query)
            for ans in name_ans:
                if len(ans)==1:
                    first_element = str(ans[0])  
            first_pro=f"The name of the head entity is {first_element}."
            cypher_query=f"""
            MATCH (n {{name: '{first_element}'}}) 
            RETURN labels(n)
            """
            answers = link1.run(cypher_query)
            entity_answers = ""
            for ans in answers:
                entity_answers += str(ans[0])  
            match = re.search(r"\['([^]]+)'\]", entity_answers)
            extracted_str = match.group(1) 
            second_element = line.split(',')[1].strip(')').strip()
            third_element=line.split(',')[2].strip(')').strip()
            com_question=f"The entity type of {first_element} is {extracted_str}."
            question=old_question+com_question
            first_element = extracted_str 
            answers = link1.run(cypher_query)
            for ans in answers:
                if isinstance(ans[0], list) and ans[0][0] == second_element:
                    target1="Detected attribute"
        elif count == 2:
            second_element=""
            matches = re.findall(r'\(([^,]+),', line)
            pattern = r"\(([^,]+),([^,]+),([^)]+)\)"
            matches2 = re.search(pattern, line)
            second_element = matches2.group(2)
            third_element = matches2.group(3)
            if len(matches) >= 2:
                a = matches[0]
                b = matches[1]
                a_cypher_query=f"""
                MATCH (e) 
                WHERE e.name_en = '{a}'
                RETURN e.name
                """
                name_ac=link1.run(a_cypher_query)
                for ans in name_ac:
                    if len(ans)==1:
                        a = str(ans[0]) 
                b_cypher_query=f"""
                MATCH (e) 
                WHERE e.name_en = '{b}'
                RETURN e.name
                """
                name_bc=link1.run(b_cypher_query)
                for ans in name_bc:
                    if len(ans)==1:
                        b = str(ans[0]) 
                cypher_querya=f"""
                MATCH (n {{name: '{a}'}}) 
                RETURN labels(n)
                """
                answersa = link1.run(cypher_querya)
                linshi_answers = ""
                for ans in answersa:
                    linshi_answers += str(ans[0])  
                matcha = re.search(r"\['([^]]+)'\]", linshi_answers)
                linshi_str = matcha.group(1) 
                cypher_queryb=f"""
                MATCH (n {{name: '{b}'}}) 
                RETURN labels(n)
                """
                answersb = link1.run(cypher_queryb)
                for ans in answersb:
                    if isinstance(ans[0], list) and ans[0][0] == second_element:
                        name_ht=f"The name of the head entity is {a} and The name of the tail entity is {b}."
                        target1="Relationship detected"
                answersa = link1.run(cypher_querya)
                for ans in answersa:
                    if isinstance(ans[0], list) and ans[0][0] == second_element:
                        name_ht=f"The name of the head entity is {a} and The name of the tail entity is {b}."
                        target1="Relationship detected"
            else:
                print("no data")
            cypher_query=f"""
            MATCH (n)
            WHERE n.name CONTAINS "{a}" AND n.name CONTAINS "{b}"
            RETURN labels(n),n.name limit 10
            """
            answers = link1.run(cypher_query)            
            entity_answers = ""
            for ans in answers:
                entity_answers += str(ans[0]) 
                first_name += str(ans[1]) + ","
            match = re.search(r"\['([^]]+)'\]", entity_answers)
            if match:
                extracted_str = match.group(1) 
                first_element = extracted_str 
            else:
                first_element=linshi_str           
            name_pro=f"The specific name of the head entity is:{first_name}."
        attr_pro=f"The selected attribute is {third_element}."

        # Create a complete diagram
        if not target1:
            G = nx.DiGraph() 
            edges = [  
                ("Drug", "Genesymbol", {"relation": "activation_to"}), 
                ("Drug", "Cancer", {"relation": "treatment"}),  
                #...
            ]  
            G.add_edges_from(edges)  

            node_information = """(Drug)-[:activation_to {}]->(Genesymbol),(Drug)-[:treatment {}]->(Cancer)...
            """
            shortest_paths = nx.all_shortest_paths(G, source=first_element, target=second_element)
            path_prompts = ""
            rel_links = [] 
            mid_eles = []
            for index, path in enumerate(shortest_paths):        
                mid_ele = path[1]
                path_prompts += str(path[1])

                rel_prompts_1 = []
                rel_prompts_2 = []
                mid_elements = []
                entity_pro=""
                links = node_information.strip('\n').split(',')
                for link in links:
                    head = link.split('-')[0].strip('(').strip(')')
                    tail = link.split('->')[1].strip('(').strip(')')
                    if second_element == mid_ele:
                        entity_pro="No intermediate entity."
                        if head == first_element and tail == mid_ele:
                            rel_prompts_1.append(str(link))
                            mid_elements.append(mid_ele)
                        if head == mid_ele and tail == first_element:
                            rel_prompts_1.append(str(link))
                            mid_elements.append(mid_ele)
                    else:                        
                        if head == first_element and tail == mid_ele:
                            rel_prompts_1.append(str(link))
                            mid_elements.append(mid_ele)
                        if head == mid_ele and tail == first_element:
                            rel_prompts_1.append(str(link))
                            mid_elements.append(mid_ele)
                        if head == second_element and tail == mid_ele:
                            rel_prompts_2.append(str(link))
                        if head == mid_ele and tail == second_element:
                            rel_prompts_2.append(str(link))

                for r_i, rel_1 in enumerate(rel_prompts_1):
                    mid_eles.append(mid_elements[r_i])
                    if rel_prompts_2 == []:
                        rel_links.append([rel_1])
                    else:
                        for rel_2 in rel_prompts_2:
                            rel_links.append([rel_1, rel_2])
            similarity_scores = []

            # Choose the optimal path
            sentence1 = old_question
            for rel_link in rel_links:
                sentence2 = ','.join(rel_link)
                similarity = calculate_similarity(sentence1, sentence2, model1, tokenizer)
                similarity_scores.append(similarity)

            selected_index = torch.tensor(similarity_scores).topk(1)[1][0]
            gxl_pro = ','.join(rel_links[selected_index])
            if len(rel_links[selected_index])>1:
                mid_ele = mid_eles[selected_index]
                entity_pro=f"The head entity type is {first_element}, the middle entity type is {mid_ele}, and the tail entity type is {second_element}."
            else:
                entity_pro="No intermediate entity."
            que_pro=f"The relationship chain pattern is {gxl_pro}."

        if target1=="Relationship detected":
            entity_pro="Relationship detected."
            name_pro=""
            que_pro=""
            first_pro=""
            attr_pro=f"{name_ht}."
        if target1=="Detected attribute":
            entity_pro="Detected attribute."
            name_pro=f"The entity type is {second_element}."
            que_pro=""
            attr_pro=""
        
        #Text2Cypher
        prompt = """
        Given a knowledge graph, answer the question according to the schema of the knowledge graph.
        The schema of the knowledge graph includes the following:
        (Drug)-[:activation_to {}]->(Genesymbol)...
        example:

        """

        question_pro="""
        Create a Cypher statement to answer the following question:
        """
        input_text1 = prompt + question_pro +old_question+first_pro+entity_pro+name_pro+que_pro+attr_pro
        sequences = pipeline1(
            input_text1,
            do_sample=True,
            top_k=10,
            return_full_text=False,
            top_p = 0.95,  
            temperature = 0.01, 
            num_return_sequences=1,
            eos_token_id=tokenizer.eos_token_id,
            max_length=4000, 
        )
        for seq in sequences:
            lines = seq['generated_text'].split('\n')
            for line in lines:
                if line.strip():  
                    break 

        cypher_query=line
        answers = link1.run(cypher_query)
        knowledge_prompts = ""
        for ans in answers:
            if len(ans) > 1:
                knowledge_prompts += f"{ans[0]} {ans[1]}\n"
            else:
                knowledge_prompts += f"{ans[0]}\n"
        lines = knowledge_prompts.split('\n')[:10]
        result_string_with_separator = '\n'.join(lines)

        #Inference
        prompt = """
        You are a reasoning robot, and you need to perform the following two steps step by step: 1. Output a corresponding natural language sentence for each relationship chain. 2. Answer my question using natural language from step 1. 
        Note: The output format is: Output: One sentence in natural language.
        For example:

        """
        input_text1 = prompt + result_string_with_separator+old_question
        sequences = pipeline1(
            input_text1,
            do_sample=True,
            top_k=10,
            return_full_text=False,
            top_p = 0.7, 
            temperature = 0.1,
            num_return_sequences=1,
            eos_token_id=tokenizer.eos_token_id,
            max_length=3000, 
        )
        for seq in sequences:
            lines = seq['generated_text'].split('\n')
            for line in lines:
                if line.strip():  
                    out=line
                    break 

            
        dataset.append(
            {
            "question":old_question,
            "answer": out
            }
        )
    except Exception as e:
        exception_(old_question)
json.dump(dataset, open('output_route', 'w', encoding='utf-8'), indent=4,ensure_ascii=False)