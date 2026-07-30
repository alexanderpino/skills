from pathlib import Path
import sys
sys.path.append('../mission-control/scripts')
from pipeline import load_llm_json

p = Path('dummy.json')
p.write_text('`json\n{\n  ""verdict"": ""green""\n}\n`')
print('Parsed:', load_llm_json(p))

p2 = Path('dummy2.json')
p2.write_text('Here is the json:\n`\n{\n  ""verdict"": ""approve""\n}\n`\nEnjoy!')
print('Parsed with preamble:', load_llm_json(p2))