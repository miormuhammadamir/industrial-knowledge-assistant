import re

def chunks(pages,size=500,overlap=75):
    if not 0<=overlap<size: raise ValueError('Invalid chunk settings')
    for page,text in pages:
        tokens=re.findall(r'\S+',text)
        step=size-overlap
        for index,start in enumerate(range(0,len(tokens),step)):
            part=tokens[start:start+size]
            if part: yield page,index,' '.join(part)
            if start+size>=len(tokens): break
