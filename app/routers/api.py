from fastapi import APIRouter, Request, Body
from typing import Dict
from services import query_service

router = APIRouter()


@router.get("/query")
def query(
    request: Request,
    question: str,
    lite: int = 0,
    max_k: int = 1,
    model: str | None = None,
    symtx_k: int | None = None,
    no_facet_fallback: int = 0,
):
    return query_service.query(
        request=request,
        question=question,
        lite=lite,
        max_k=max_k,
        model=model,
        symtx_k=symtx_k,
        no_facet_fallback=no_facet_fallback,
    )


@router.get("/demo/search")
def demo_search_get(
    request: Request,
    question: str,
    topic_key: str | None = None,
    qtype: str | None = None,
    lite: int = 0,
    max_k: int = 1,
    model: str | None = None,
    symtx_k: int | None = None,
    no_facet_fallback: int = 0,
):
    return query_service.demo_search_compat_response(
        request=request,
        question=question,
        topic_key=topic_key,
        qtype_hint=qtype,
        lite=lite,
        max_k=max_k,
        model=model,
        symtx_k=symtx_k,
        no_facet_fallback=no_facet_fallback,
    )


@router.post("/demo/search")
def demo_search_post(request: Request, payload: Dict = Body(default={})):
    question = (payload or {}).get("question", "")
    return query_service.demo_search_compat_response(
        request=request,
        question=question,
        topic_key=(payload or {}).get("topic_key"),
        qtype_hint=(payload or {}).get("qtype"),
        lite=int((payload or {}).get("lite", 0) or 0),
        max_k=int((payload or {}).get("max_k", 1) or 1),
        model=(payload or {}).get("model"),
        symtx_k=(payload or {}).get("symtx_k"),
        no_facet_fallback=int((payload or {}).get("no_facet_fallback", 0) or 0),
    )


@router.get("/llm_only")
def llm_only(request: Request, question: str | None = None, model: str | None = None):
    return query_service.llm_only(request=request, question=question, model=model)


@router.get("/health")
def health():
    return query_service.health()
