"""Agentes especialistas (Pydantic AI + Gemini). Cada uno es un módulo.

  agente_clasificador  nodo 2b: intención + tipo de dato, solo si ninguna regla coincide
  agente_sitios        redacta con la base verificada (sitios y documentos); sin herramientas, sin web
  agente_saberes       cascada narrativa N1 -> N2 -> N3 con herramientas; el orden lo impone el código

Los especialistas SIN LLM (eventos, movilidad, compartir e itinerario, datos prácticos) son funciones
deterministas en servicios/herramientas/.

Privacidad: a Gemini solo se le envía el texto de la pregunta (sin números ni correos) y el contexto
recuperado de la base. Nunca la ubicación, el contacto ni datos de la persona.
"""
