# GraderRepo

File saving system: 
- Contest oficial problem and solution: data/{CONTEST_NAME}/{YEAR}.cleaned.jsonl
- Student(model) solution: outputs/{MODEL_NAME}/{CONTEST_NAME}-{YEAR}.jsonl
    - Needs to separate the JSONL file into separate tex files:  {CONTEST_NAME}-{YEAR}-prob{problem_number}.tex for each problem from that specific contest.
- Grading are stored based on the model that is grading and the model graded: outputs/grades/{grader_name}/{graded_name}/{CONTEST_NAME}-{YEAR}-prob{problem_number}.json (to be changed to TEX).

Adding new contests to our dataset:
- Save the contest you wish to add to the data folder, but make sure it is MathJax compatible. (I think it depends on the source the way it is formatted so there is no standard formula)
- gemini.py / openai_helper.py generate their respective models soltuions to problems found in the data folder.
- gemini_grader.py / openai_grader.py grades files in the outputs for any gemini/openai generated solutions (also needs official_loader.py in order to properly access "model" grading system if wanted and official solution)
