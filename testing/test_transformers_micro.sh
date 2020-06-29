# test_transformers_micro.sh


context="EachHypertext Transfer Protocol (HTTP) message is either a request or a response.A server listens on a connection for a request, parses each message received,interprets the message semantics in relation to the identified requesttarget, and responds to that request with one or more response messages.A client constructs request messages to communicate specific intentions,examines received responses to see if the intentions were carried out,and determines how to interpret the results. This document defines HTTP/1.1request and response semantics in terms of the architecture defined in[RFC7230]. HTTP provides a uniform interface for interacting with a resource(Section 2), regardless of its type, nature , or implementation, via themanipulation and transfer of representations ( Section 3)."

questions=(
    'what is http?'
    'what does a server do?'
    'what is the purpose of this document?'
    'what is a hot dog?'
)

for question in "${questions[@]}"; do
    echo "${question}"
    curl -XPOST http://localhost:8081/question -H 'content-type:application/json' -d "
    {
        \"question\": \"${question}\",
        \"context\": \"${context}\"
    }
"
    echo "";
done

