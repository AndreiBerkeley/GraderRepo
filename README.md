# GraderRepo

File saving system: 
- Contest oficial problem and solution: data/{CONTEST_NAME}/{YEAR}.cleaned.jsonl
- Student(model) solution: outputs/{MODEL_NAME}/{CONTEST_NAME}-{YEAR}.jsonl
    - Needs to separate the JSONL file into separate TeX files:  {CONTEST_NAME}-{YEAR}-prob{problem_number}.tex for each problem from that specific contest.
- Grading is stored based on the model that is grading and the model graded: outputs/grades/{grader_name}/{graded_name}/{CONTEST_NAME}-{YEAR}-prob{problem_number}.json (to be changed to TEX).

Adding new contests to our dataset:
- Save the contest you wish to add to the data folder, but make sure it is MathJax compatible. (I think it depends on the source, the way it is formatted,d so there is no standard formula)
- gemini.py / openai_helper.py generate their respective model solutions to problems found in the data folder.
- gemini_grader.py / openai_grader.py grades files in the outputs for any gemini/openai generated solutions (also needs official_loader.py in order to properly access the "model" grading system if wanted and official solution)

Platform Handler:
- viewer.py: automatically detects any new models and adds them to the dropdown menu. (to be added for grader)
- static/viewer.html: handles platform generation as well as review/comment saving. (minor edits for ease of use still in progress)


Currently, both the grader and generator analyze complete folders: 
- Solution to target specific contest-year pairing:
      - set CONTEST_FILTER ; YEAR_FILTER in your terminal to the {CONTEST_NAME} ; {CONTEST_YEAR} you wish to process.
      - Delete the comments for the necessary parts in the file processing in gemini.py / openai_helper.py ; gemini_grader.py / openai_grader.py .
