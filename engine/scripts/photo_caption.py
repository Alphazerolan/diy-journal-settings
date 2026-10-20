"""Shared caption wrapping; photo width changes line breaks, never font size."""
import unicodedata

def units(text):
    return sum(0 if unicodedata.combining(c) else .33 if c.isspace() else 1 if unicodedata.east_asian_width(c) in ('W','F') else .6 for c in text)

def lines(text,capacity,max_lines=2):
    remaining=text.strip();result=[];capacity=max(2,capacity)
    while remaining and len(result)<max_lines:
        line=''
        while remaining and units(line+remaining[0])<=capacity:
            line+=remaining[0];remaining=remaining[1:]
        if len(result)==max_lines-1 and remaining:
            while line and units(line+'…')>capacity:line=line[:-1]
            line+='…'
        result.append(line.strip());remaining=remaining.lstrip()
    return result
