import re, collections, csv
from collections import defaultdict
import pandas as pd
from anytree import Node, RenderTree, findall, findall_by_attr, find_by_attr
from tf.app import use
A = use('bhsa', hoist=globals(), mod='ch-jensen/participants/actor/tf', silent=True)

class GenerateNodes:

    def __init__(self, book, chapter):
        self.book = book
        self.chapter = chapter
    
    def nodeList(self):
        '''
        Generates a node list consisting of all phrase atom-,suphrase- and word-nodes of given book and chapter.
        '''
        chapter_node = T.nodeFromSection((self.book, self.chapter))
        phrase_atom_list = L.d(chapter_node, 'phrase_atom')

        node_list = []
        for n in phrase_atom_list:
            node_list.append(n)
            for subph in L.d(n, 'subphrase'):
                node_list.append(subph)
            for w in L.d(n, 'word'):
                node_list.append(w)

        return node_list
    
    def actorLabel(self, n, t='string'):
        '''
        Input: node
        Output: actor (proper name, full nominal phrase, pronoun or suffix)
        '''
        actor_str = ''
        actor_n = []
        typ = ['PrNP','NP','PP','PPrP','DPrP']
        vt = [['perf','impf','wayq','impv'],['infa','infc','ptca','ptcp']]

        edges = sorted((n,) + E.coref.f(n)) #Getting edges and adding the requested node to the tuple

        ## 1. Proper noun phrases, nominal phrases, prepostional phrases, pronominal phrases, demonstrative phrases
        nr = 0
        if len(edges) > 1:
            while not actor_str and nr < 5:
                for e in edges:
                    if F.typ.v(e) == typ[nr]:
                        for w in L.d(e, 'word'):

                            #a. Checking phrase dependent part of speech
                            if F.pdp.v(w) in ['nmpr','subs','prps']:
                                actor_str += F.lex.v(w)
                                actor_n.append(w)

                                #b. If pronominal suffix, the actor is found by calling actor() recursively.
                                if F.prs.v(w) not in ['absent','n/a']:
                                    actor_str += '-' + self.actorLabel(w)

                            #c. If preposition, the preposition itself is ignored but its possible pro.suffix is found with actor()
                            elif F.sp.v(w) == 'prep' and F.prs.v(w) not in ['absent','n/a']:
                                actor_str += '-' + self.actorLabel(w) #Finding actor of suffix by calling actor().
                        break
                nr += 1

        ## 2. Subphrases
        if len(edges) > 1 and not actor_str:
            for e in edges:
                if F.otype.v(e) == 'subphrase':
                    for w in L.d(e, 'word'):
                        if F.pdp.v(w) in ['nmpr','subs','prps']: #Checking part of speech
                            actor_str += F.lex.v(w)
                            actor_n.append(w)
                            if F.prs.v(w) not in ['absent','n/a']:
                                actor_str += '-' + self.actorLabel(w)
                    break

        ## 3. Verb phrases
        if len(edges) > 1 and not actor_str:
            nr = 0
            while nr < 2:
                for e in edges:
                    if F.typ.v(e) == 'VP':
                        for w in L.d(e, 'word'):
                            if F.sp.v(w) == 'verb' and F.vt.v(w) in vt[nr]:
                                if F.vt.v(w) not in ['infc','infa','ptca','ptcp']:

                                    #Extracting number, gender and person to use as actor information:
                                    actor_str = f'{F.ps.v(w)[1]}{F.gn.v(w)}{F.nu.v(w)[0]}'
                                    actor_n.append(w)
                                else:
                                    #Using the verb lexeme itself as actor
                                    actor_str = F.lex.v(w)
                                    actor_n.append(w)
                    if actor_str:
                        break
                nr += 1
        
        ## 4. Suffixes
        if len(edges) > 1 and not actor_str:
            for e in edges:
                if F.otype.v(e) == 'word':
                    if F.prs.v(e) not in ['absent','n/a']:
                        actor_str = f'{F.prs_ps.v(e)[1]}{F.prs_gn.v(e)}{F.prs_nu.v(e)[0]}_sfx'
                        break

        if len(edges) > 1 and not actor_str:
            return 'error'
        elif t == 'node':
            return actor_n
        else:
            return re.sub('[/[]', ' ', actor_str)
        
    def checkActorDict(self, actor_dict, actor_string, coref):
        #If the reference node already occurs in the dictioanry, continue.
        if coref[0] in [x for v in actor_dict.values() for x in v]:
            return

        #If the node is new, check whether its actor reference exists in the dictionary
        else:

            if actor_string not in actor_dict:
                actor_dict[actor_string] = coref
                return actor_dict

            #If actor reference exists, we need to create a new actor reference to avoid overwriting different, but
            #identical actors.
            else:

                new_actor = ''
                n=2

                while not new_actor:
                    if f'{actor_string}#{n}' not in actor_dict:
                        new_actor = f'{actor_string}#{n}'
                        actor_dict[new_actor] = coref
                        return actor_dict
                    else:
                        n+=1
                        
    def actorDict(self):

        actor_dict = {}

        for n in self.nodeList():
            actor_str = self.actorLabel(n).rstrip()
            coref_n = list((n,) + E.coref.f(n))

            if actor_str:

                self.checkActorDict(actor_dict, actor_str, coref_n) 

        return actor_dict
    
    def allRefs(self):
        actor_dict = self.actorDict()

        for n in self.nodeList():
            if not E.coref.f(n):
                if F.otype.v(n) in ['phrase_atom']:
                    if F.function.v(L.u(n, 'phrase')[0]) in ['Subj','Objc','Cmpl','PreS','PreO']:
                        actor_str = ''
                        for w in L.d(n, 'word'):
                            if F.sp.v(w) == 'prep' and  F.prs.v(w) not in ['absent','n/a']:
                                continue
                            else:
                                actor_str += f'{F.lex.v(w)} '
                                if F.prs.v(w) not in ['absent','n/a']:
                                    actor_str += '-' + self.actorLabel(w)

                        actor_str = actor_str.rstrip()
                        if actor_str:
                            self.checkActorDict(actor_dict, actor_str, [n])
                            
        self.AllRefs = actor_dict
        return actor_dict
    
    def tree(self, selected_refs, synonyms, hyponyms):
        
        #Adding lists to class:
        self.selected_refs = selected_refs
        self.synonyms = synonyms
        self.hyponyms = hyponyms
        
        participants = Node('participants')

        ##hyponyms
        for hyp in self.hyponyms:
            if not findall_by_attr(participants, hyp):
                hypo = Node(hyp, parent=participants)
                for hyper in self.hyponyms[hyp]:
                    hyper = Node(hyper, parent=hypo)

            else:
                for hyper in self.hyponyms[hyp]:
                    hypo = find_by_attr(participants, hyp)
                    hyper = Node(hyper, parent=hypo)

        ##synonyms
        for syn in self.synonyms:
            overlap = findall_by_attr(participants, syn) 
            if overlap: #The synonym already exists in the tree
                for n in overlap:
                    syno = find_by_attr(n, syn)
                    for s in self.synonyms[syn]:
                        s0 = Node(s, parent=syno) #Creating node
                        s1 = Node(syno.name, parent=s0) #Creating additional node for doubling and reversing the edge.
            else: #If the synonym does not exist in the tree
                syno = Node(syn, parent=participants) #Creating node
                for s in self.synonyms[syn]:
                    s0 = Node(s, parent=syno) #Creating synonym
                    s1 = Node(syno.name, parent=s0) #Reverse node
                
        ##remaining participants
        for n in self.selected_refs:
            if not findall_by_attr(participants, n):
                node = Node(n, parent=participants)    

        self.tree = participants
        return participants
    
    def treeStructure(self):
        for pre, fill, node in RenderTree(self.tree):
            print("%s%s" % (pre, node.name))
    
    def resultRefs(self):
        result_dict = defaultdict(list)

        for actor in self.AllRefs:
            if actor in self.selected_refs:
                
                ##Synonyms
                if actor in [x for v in self.synonyms.values() for x in v]:
                    for syn in self.synonyms:
                        if actor in self.synonyms[syn]:        
                            result_dict[syn] += self.AllRefs[actor]
                
                ##Remaining actors
                else:
                    result_dict[actor] += self.AllRefs[actor]
                    
        for actor in self.AllRefs:
                
            ##Hyponyms
            if actor in self.hyponyms:
                for hypo in self.hyponyms[actor]:
                    hypers = findall_by_attr(self.tree, hypo) #Finding all hypernyms of the given actor using the tree.
                    for hyper in hypers: #Looping over all possible hypernyms
                        for parent in hyper.ancestors: #Looping over all ancestors and extracting each particular parent.
                         
                            #The hyponym is compared with the hypernym. If equal, they are synonyms and thus ignored.
                            #If un-equal, it is indeed a hyponym and the references of the hypernym is transferred to
                            #the hyponym.
                            if parent.name != 'participants' and hypo != parent.name and parent.name not in [x for v in self.synonyms.values() for x in v]:
                                    
                                #If the references are not already stored for the given actor, they are added to the dict.
                                if not result_dict[parent.name][0] in result_dict[hypo]:
                                    result_dict[hypo] += result_dict[parent.name]
                                        
        self.result_dict = result_dict
        return result_dict
    
    def checkResults(self):
        '''
        The function validates resulting dictionary consisting of selected references, and possibly synonyms and hyponyms.
        The resulting dictionary is validated against the original dictionary of all actors and their references of a particular
        chapter and synonyms and hyponyms are taken into account.

        The procedure consists of 4 steps:
        1. Checking whether all actors of the selected actors are included in the resulting list (except synonyms)
        2. Checking whether references are missing from the resulting dict in comparison to the original dict.
        3. Checking whether there are unexpected references in the resulting dict (appart from references derived from
        synonyms and hyponyms.)
        '''
        error_list = []
        result_actors = [actor for actor in self.result_dict]

        ## 1. check: Are all human participants represented in the resulting list(except synonyms)?
        for actor in self.selected_refs:

            #Check whether selected referent is in resulting list and in synonym-dictionary:
            if actor not in result_actors and actor not in [x for v in self.synonyms.values() for x in v]:
                error_list.append(("error#1", actor, a))

        ## 2. and 3. check: Are refs missing in the resulting list? Or are there unexpected refs?
        for actor in result_actors:

            identified = False
            for a in self.AllRefs[actor]: #Looping over refs of original list

                ## 2. check: Are refs missing from the resulting list?
                if a not in self.result_dict[actor]: #Does the ref exist in the resulting list?
                    error_list.append(("error#2", actor, a))

                ## 3. check: Does the resulting list contain unexpected ref-nodes?
                elif a not in self.AllRefs[actor]: #Does the ref exist in the original list?

                    ##3a. Checking whether mismatch is due to synonyms (refs are transferred from synonymous words)
                    if actor in self.synonyms:
                        for syn in self.synonyms[actor]:
                            if a in self.AllRefs[syn]:
                                identified = True

                        if not identified:

                            ##3b. Checking whether the synonym is also a hyponym (refs are derived from hypernyms)
                            if actor in [x for v in self.hyponyms.values() for x in v]:
                                for k, v in self.hyponyms.items():
                                    for hypo in v:
                                        if hypo == actor:
                                            if a in self.AllRefs[k]:
                                                identified = True

                                if not identified:
                                    error_list.append(("error#3b", actor, a))


                            else:
                                error_list.append(("error#3a", actor, a))

                    ##3c. Checking whether mismatch is due to hyponyms (refs are derived from hypernyms)
                    elif actor in [x for v in self.hyponyms.values() for x in v]:
                        for k, v in self.hyponyms.items():
                            for hypo in v:
                                if hypo == actor:
                                    if a in self.AllRefs[k]:
                                        identified = True

                        if not identified:
                            error_list.append(("error#3c", actor, a))

                    ##3.d Neither synonym or hyponym.
                    else:
                        error_list.append(("error#3d", actor, a))

        return error_list
    
class ValidateNodes:
    
    def __init__(self, book, chapter, path, file):
        self.book = book
        self.chapter = chapter
        self.datapath = f'{path}{file}'
        
    def validate(self):
        new_object = GenerateNodes(self.book, self.chapter)
        
        actor_dict = new_object.actorDict()
        orig_data = pd.read_csv(self.datapath)

        for actor in actor_dict:
            for n in actor_dict[actor]:
                orig_data_actor = orig_data[orig_data.otype == str(n)].actor.item()
                if actor != orig_data_actor:
                    print(f'Node: {n} :: Generated: {actor} :: Dataset: {orig_data_actor}')