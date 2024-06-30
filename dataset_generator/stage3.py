from datasets import Dataset
from transformers import Pipeline
from tqdm.auto import tqdm
from .utils import generate_completions
import logging


def generate_corrective_dataset(incorrect_solution_dataset: Dataset, corrective_prompt: str, supervisor_pipe: Pipeline, extract_answer_function: callable, corrective_solution_count_per_incorrect_solution: int = 1, correction_attempts = 5, generate_kwargs = {}) -> Dataset:
    result_original_prompts = []
    result_incorrect_solutions = []
    result_correction_prompts = []
    result_corrective_completions = []
    
    for row in tqdm(incorrect_solution_dataset.iter(1), total=len(incorrect_solution_dataset)):
        prompt_with_problem = corrective_prompt.format(problem=row["problem"][0], incorrect_solution=row["completion"][0], correct_answer=row["correct_answer"][0], incorrect_answer=row["generated_answer"][0])
        
        correct_completion = []
        attempt = 0
        while len(correct_completion) < corrective_solution_count_per_incorrect_solution and attempt < correction_attempts:
            completions = generate_completions(supervisor_pipe, prompt_with_problem, corrective_solution_count_per_incorrect_solution, generate_kwargs)
            correct_completion += [completion for completion in completions if extract_answer_function(completion) == row["correct_answer"][0]]
            attempt += 1
        
        if len(correct_completion) == 0:
            logging.debug(f"Failed to generate corrective completion for problem: {row['problem'][0]}")
        new_data_count = len(correct_completion)
        result_original_prompts += [row["prompt"][0]] * new_data_count
        result_incorrect_solutions += [row["completion"][0]] * new_data_count
        result_correction_prompts += [prompt_with_problem] * new_data_count
        result_corrective_completions += correct_completion[:new_data_count]
        
    return Dataset.from_dict({
        "original_prompt": result_original_prompts,
        "incorrect_completion": result_incorrect_solutions,
        "correction_prompt": result_correction_prompts,
        "correct_completion": result_corrective_completions
    })
    
    
def generate_kto_dataset(correction_dataset: Dataset) -> Dataset:
    result_prompts = []
    result_completions = []
    result_labels = []
    
    for row in tqdm(correction_dataset.iter(1), total=len(correction_dataset)):
        result_prompts.append(row["original_prompt"][0])
        result_completions.append(row["incorrect_completion"][0])
        result_labels.append(False)
        
        result_prompts.append(row["original_prompt"][0])
        result_completions.append(row["correct_completion"][0])
        result_labels.append(True)
        
    return Dataset.from_dict({
        "prompt": result_prompts,
        "completion": result_completions,
        "label": result_labels,
    })