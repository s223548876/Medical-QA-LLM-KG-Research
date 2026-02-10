from fastapi import Request
from services import query_service


def query(request: Request,
          question: str,
          lite: int = 0,
          max_k: int = 1,
          model: str | None = None,
          symtx_k: int | None = None,
          no_facet_fallback: int = 0):
    return query_service.query(
        request=request,
        question=question,
        lite=lite,
        max_k=max_k,
        model=model,
        symtx_k=symtx_k,
        no_facet_fallback=no_facet_fallback,
    )


def _demo_search_compat_response(
    request: Request,
    question: str,
    lite: int = 0,
    max_k: int = 1,
    model: str | None = None,
    symtx_k: int | None = None,
    no_facet_fallback: int = 0
):
    return query_service.demo_search_compat_response(
        request=request,
        question=question,
        lite=lite,
        max_k=max_k,
        model=model,
        symtx_k=symtx_k,
        no_facet_fallback=no_facet_fallback,
    )


def llm_only(request: Request, question: str | None = None, model: str | None = None):
    return query_service.llm_only(request=request, question=question, model=model)


def health():
    return query_service.health()
