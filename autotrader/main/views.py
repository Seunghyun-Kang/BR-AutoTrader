from django.shortcuts import render
import requests
import json
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view

def index(request):
    return render(request,'main/index.html')

@api_view(['POST'])
def doTrade(request):
    print("DO TRADE")
    try:
        data = request.data.dict()
        for item in data:
            print(f"{item} -- {data[item]}")
        return Response(status=status.HTTP_200_OK)
    except:
        return Response(status=status.HTTP_400_BAD_REQUEST)
    