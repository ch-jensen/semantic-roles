import subprocess

class Logos:
    
    def __init__(self, path='C:/Users/Ejer/AppData/Local/Logos/', bible='bhssesb'):
        self.path = path
        self.bible = bible
        
    def link(self, reference=tuple()):
    
        bo, ch, ve = reference
        logos_link = f'logosres:{self.bible};ref=BibleBHS.{bo}{ch}.{ve}'
    
        #Open Logos
        p = subprocess.Popen([f'{self.path}Logos.exe', logos_link])