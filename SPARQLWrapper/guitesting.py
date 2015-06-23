# -*- coding: utf-8 -*-
"""
Created on Wed May 06 12:22:33 2015

@author: anujkumar
"""
from Tkinter import *
import Tkinter
import tkMessageBox

top = Tkinter.Tk()


#-----------------#

from SPARQLWrapper import SPARQLWrapper, JSON

import rdflib

"""
results = sparql.query().convert()

for result in results["results"]["bindings"]:
    print result["label"]["value"]
"""

#################



text = Text(top)
text.pack()

L1 = Label(top, text="ENTER YOUR SPARQL QUERY HERE : ")
L1.pack( side = TOP)


L2 = Label(top, text="Enter sparql end-point : ")
L2.pack( side = LEFT)

E3 = Entry(top, bd =5  )
E3.pack(side = LEFT)

L3 = Label(top, text="Enter return format : ")
L3.pack( side = LEFT)

E4 = Entry(top, bd =5  )
E4.pack(side = LEFT)

L4 = Label(top, text="Enter graph : ")
L4.pack( side = LEFT)

E5 = Entry(top, bd =5  )
E5.pack(side = LEFT)

def GraphData( ) :
   if E5.get( ) :
       print "hello world"
       f = open( "subpredobj.txt" , "wb" )
       ############
       #in terms of general subject predicate object manner
       g = rdflib.Graph()
       tempresult = g.parse(str(E5.get( )) )

       f.write("graph has %s statements." + str( len(g))+ "\n" )
# prints graph has 79 statements.

       for subj, pred, obj in g:
    
           f.write( (str( subj ) + "  " + str( pred ) + "  " + str( obj )  )+ "\n"+"\n" )
       f.close( )    
       #######
       
       #########
       #in terms of Turutle or N3 format
       #most of the semnatic examples have considered turtle and n3 to follow the same
       #format
       f = open( "n3.txt" , "wb" )
#       g = rdflib.Graph( )
 #      tempresult = g.parse( str( E.get( ) ) )
       #for subj, pred, obj in g :
       f.write( g.serialize( format = 'n3' ) )
       f.close( )
       ##########
       #########
       #in terms of Turutle or N3 format
       #most of the semnatic examples have considered turtle and n3 to follow the same
       #format
       f = open( "turtle.txt" , "wb" )
#       g = rdflib.Graph( )
 #      tempresult = g.parse( str( E.get( ) ) )
       #for subj, pred, obj in g :
       f.write( g.serialize( format = 'turtle' ) )
       f.close( )
       
       ###############
       
       ######
       # in terms of rdf format
       f= open( "xmlfile.txt" , "wb" )
       f.write( g.serialize( format = 'xml') ) 
       f.close( )
       
def helloCallBack():
   sparql = SPARQLWrapper( E3.get( ) ) 
   sparql.setQuery(
    text.get( "1.0" , END )   
   )
   
   sparql.setReturnFormat( E4.get() )
   results = sparql.query().convert()
   message = ""
   for result in results["results"]["bindings"]:
       message = message + str(result["label"]) + "\n"
   tkMessageBox.showinfo( "Hello Python", message )
   
   if E5.get( ) :
       print "hello world"
       f = open( "subpredobj1.txt" , "wb" )
       ############
       #in terms of general subject predicate object manner
       g = rdflib.Graph()
       result = g.parse(str( E5.get( )) )

       f.write("graph has %s statements." + str( len(g))+ "\n" )
# prints graph has 79 statements.

       for subj, pred, obj in g:
    
           f.write( str( subj ) + "  " + str( pred ) + "  " + str( obj ) + "\n" ) 
       ##########        
       
       
   
       
        
   
   #m = text.get("1.0",END ).splitlines( )
   print( text.get( "1.0" , END ) )

B = Tkinter.Button(top, text ="ExecuteQuery", command = helloCallBack)
T = Tkinter.Button(top, text ="RunGraph", command = GraphData)

T.pack()
B.pack()
top.mainloop( )