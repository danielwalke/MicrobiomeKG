docker stop $(docker ps -q --filter ancestor=neo4j:latest) && docker rm $(docker ps -aq --filter ancestor=neo4j:latest)
