import rdflib

g = rdflib.Graph()
result = g.parse("http://www.w3.org/People/Berners-Lee/card")

print("graph has %s statements." % len(g))
# prints graph has 79 statements.

for subj, pred, obj in g:
    
   print("anuj" + str( subj ) + "  " + str( pred ) + "  " + str( obj ) )
   if (subj, pred, obj) not in g:
       raise Exception("It better be!")

#s = g.seri



from SPARQLWrapper import SPARQLWrapper, JSON

sparql = SPARQLWrapper("http://dbpedia.org/sparql")
sparql.setQuery("""
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    SELECT ?label
    WHERE { 
      <http://dbpedia.org/resource/Asturias> rdfs:label ?label .
    }
""")
sparql.setReturnFormat(JSON)
results = sparql.query().convert()

for result in results["results"]["bindings"]:
    print result["label"]["value"]