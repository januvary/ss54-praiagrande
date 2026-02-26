# SS-54 Frontend V2 - Content Configuration
# All text, labels, and document requirements for the frontend

from typing import cast

SITE = {
    "name": "SS-54",
    "title": "Solicitações SS-54",
    "subtitle": "Assistência Farmacêutica de Praia Grande",
    "whatsapp": "https://wa.me/5513999999999",
    "description": "Solicitação de medicamentos, nutrição enteral e bomba de insulina através da Comissão de Farmácia do Estado de São Paulo",
}

PROCESS_TYPES = {
    "medicamento": {
        "title": "Medicamento",
        "description": "Solicitação de medicamentos para tratamento de doenças crônicas",
        "long_description": "Inicie um novo processo de solicitação de medicamento através da Comissão de Farmácia do Estado de São Paulo",
        "icon": "pill",
    },
    "nutricao": {
        "title": "Nutrição Enteral",
        "description": "Solicitação de fórmulas de nutrição enteral",
        "long_description": "Solicitação de fórmulas de nutrição enteral para tratamento domiciliar",
        "icon": "droplet",
        "note": "",
    },
    "bomba": {
        "title": "Bomba de Insulina",
        "description": "Solicitação de bomba de infusão de insulina",
        "long_description": "Solicitação de bomba de infusão contínua de insulina para tratamento de diabetes",
        "icon": "activity",
        "note": "",
    },
}

DOCUMENT_REQUIREMENTS = {
    "medicamento": [
        {
            "id": 1,
            "title": "Formulário de Avaliação",
            "required": True,
            "download": "/files/FORMULARIO_MEDICAMENTOS.pdf",
            "note": "Deve estar completamente preenchido, legível e com todas as assinaturas:",
            "bullet_points": [
                "Paciente ou Responsável",
                "Médico prescritor",
                "Diretor/Responsável da Instituição",
            ],
            "footer": "No caso de consultórios em que o médico prescritor é o próprio responsável da instituição, ele deverá assinar nos dois campos.",
        },
        {
            "id": 2,
            "title": "Declaração de Inexistência de Conflito de Interesses",
            "required": True,
            "download": "/files/DECLARACAO_CONFLITO_INTERESSES.pdf",
            "note": "Declaração de inexistência de conflito de interesses em relação à indústria farmacêutica e/ou pesquisa clínica, assinada pelo médico prescritor, conforme a Resolução-SS 83 de 17-08-2015",
        },
        {
            "id": 3,
            "title": "Receita Médica",
            "required": True,
            "note": "Legível, com o <strong>nome genérico do medicamento</strong> e data inferior a 30 dias",
        },
        {
            "id": 4,
            "title": "Relatório Médico",
            "required": True,
            "note": "Relatório evolutivo atualizado justificando a necessidade do item não preconizado no SUS",
        },
        {
            "id": 5,
            "title": "Exames Complementares",
            "required": False,
            "note": "Exames laboratoriais e/ou de imagem que comprovem a necessidade do medicamento",
        },
        {
            "id": 6,
            "title": "Documentos Pessoais",
            "required": True,
            "note": "Documentos necessários:",
            "bullet_points": ["RG", "CPF", "Cartão SUS", "Comprovante de residência"],
            "footer": "<strong>Paciente menor de idade:</strong> cópia do documento do responsável.<br><strong>Nome de outra pessoa no comprovante:</strong> cópia do documento da pessoa.",
        },
    ],
    "nutricao": [
        {
            "id": 1,
            "title": "Formulário de Avaliação",
            "required": True,
            "download": "/files/FORMULARIO_NUTRICAO_ENTERAL.pdf",
            "note": "Deve estar completamente preenchido, legível e com todas as assinaturas:",
            "bullet_points": [
                "Paciente ou Responsável",
                "Médico prescritor",
                "Nutricionista",
                "Diretor/Responsável da Instituição",
            ],
            "footer": "No caso de consultórios em que o médico prescritor é o próprio responsável da instituição, ele deverá assinar nos dois campos.",
        },
        {
            "id": 2,
            "title": "Declaração de Conflito de Interesses",
            "required": True,
            "download": "/files/DECLARACAO_CONFLITO_INTERESSES.pdf",
            "note": "Declaração de inexistência de conflito de interesses em relação à indústria farmacêutica e/ou pesquisa clínica, assinada pelo médico prescritor, conforme a Resolução-SS 83 de 17-08-2015",
        },
        {
            "id": 3,
            "title": "Receita Médica/Nutricional",
            "required": True,
            "note": "Legível, com o <strong>nome genérico da fórmula enteral, volume/posologia, via de acesso</strong> e data inferior a 30 dias",
        },
        {
            "id": 4,
            "title": "Relatório Médico",
            "required": True,
            "note": "Relatório evolutivo atualizado justificando a necessidade do item não preconizado no SUS",
        },
        {
            "id": 5,
            "title": "Exames Complementares",
            "required": False,
            "note": "Exames laboratoriais e/ou de imagem que comprovem a necessidade da nutrição enteral<br>",
            "bullet_points": [
                "<strong>Paciente Oncológico:</strong> Laudo do exame anatomopatológico (não há necessidade para Leucemia)<br>",
                "<strong>Fórmula Infantil (>2 anos) para APLV (Alergia à Proteína do Leite da Vaca):</strong> Laudo constando teste de provocação (últimos 3 meses)<br>",
                "<strong>Fórmula para doenças metabólicas (Erros inatos do metabolismo):</strong> Exames comprobatórios da patologia, receita constando quantidade necessária em g/dia",
            ],
        },
        {
            "id": 6,
            "title": "Documentos Pessoais",
            "required": True,
            "note": "Documentos necessários:",
            "bullet_points": ["RG", "CPF", "Cartão SUS", "Comprovante de residência"],
            "footer": "<strong>Paciente menor de idade:</strong> cópia do documento do responsável.<br><strong>Nome de outra pessoa no comprovante:</strong> cópia do documento da pessoa.",
        },
    ],
    "bomba": [
        {
            "id": 1,
            "title": "Formulário de Avaliação",
            "required": True,
            "download": "/files/FORMULARIO_MEDICAMENTOS.pdf",
            "note": "Deve estar completamente preenchido, legível e com todas as assinaturas:",
            "bullet_points": [
                "Paciente ou Responsável",
                "Médico prescritor",
                "Diretor/Responsável da Instituição",
            ],
            "footer": "No caso de consultórios em que o médico prescritor é o próprio responsável da instituição, ele deverá assinar nos dois campos.",
        },
        {
            "id": 2,
            "title": "Declaração de Conflito de Interesses",
            "required": True,
            "download": "/files/DECLARACAO_CONFLITO_INTERESSES.pdf",
            "note": "Declaração de inexistência de conflito de interesses em relação à indústria farmacêutica e/ou pesquisa clínica, assinada pelo médico prescritor, conforme a Resolução-SS 83 de 17-08-2015",
        },
        {
            "id": 3,
            "title": "Receita Médica",
            "required": True,
            "note": "Legível, com data inferior a 30 dias",
        },
        {
            "id": 4,
            "title": "Relatório Médico",
            "required": True,
            "note": "Constando a evolução da hemoglobina glicada, com justificativa da indicação da bomba de insulina, <strong>constando se já possui bomba (informar modelo)<strong>",
        },
        {
            "id": 5,
            "title": "Exames Necessários",
            "required": True,
            "download": "/files/FICHA MONITORAMENTO GLICEMIA.pdf",
            "note": "• Três resultados de hemoglobina glicada dos últimos 12 meses (caso não possua 3, apresentar justificativa)<br><br>Caso já utilizar bomba:<br>• Relatório extraído da memória da bomba (período mínimo de 30 dias)<br><br>Caso utilizar dispositivo de controle de glicemia instesticial (ex: Freestyle Libre):<br>• Relatório extraído da memória do libre (AGP libre, relatório diário libre)<br><br>Caso não utilizar bomba:<br>Relatório extraído da memória do glicosímetro do paciente contendo:",
            "bullet_points": [
                "Glicemia média",
                "Desvio padrão (DP) ou coeficiente de variação (CV)",
                "Número de medidas de glicemia capilar",
                "% tempo acima de 180mg/dl",
                "% tempo entre 70-180mg/dl",
                "% tempo <70mg/dl",
                "Tabela com valores de glicemia medidos diariamente",
            ],
        },
        {
            "id": 6,
            "title": "Documentos Pessoais",
            "required": True,
            "note": "Documentos necessários:",
            "bullet_points": ["RG", "CPF", "Cartão SUS", "Comprovante de residência"],
            "footer": "<strong>Paciente menor de idade:</strong> cópia do documento do responsável.<br><strong>Nome de outra pessoa no comprovante:</strong> cópia do documento da pessoa.",
        },
    ],
}

# Renovation-specific field overrides: (process_type, doc_id, field) -> new_value
_RENOVATION_OVERRIDES = {
    (
        "medicamento",
        4,
        "note",
    ): "Relatório evolutivo atualizado justificando a continuidade do tratamento",
    (
        "nutricao",
        4,
        "note",
    ): "Relatório evolutivo atualizado justificando a continuidade do tratamento",
    ("nutricao", 5, "bullet_points"): [
        "<strong>Fórmula Infantil (>2 anos) para APLV (Alergia à Proteína do Leite da Vaca):</strong> Laudo constando teste de provocação (últimos 3 meses)<br>",
        "<strong>Fórmula para doenças metabólicas (Erros inatos do metabolismo):</strong> Receita constando quantidade necessária em g/dia",
    ],
    ("bomba", 5, "title"): "Exames",
}


def _build_renovation_requirements() -> dict:
    """Build renovation requirements from base DOCUMENT_REQUIREMENTS with overrides."""
    renovation = {}
    for process_type, docs in DOCUMENT_REQUIREMENTS.items():
        filtered_docs = []
        for doc in docs:
            doc_id = cast(int, doc["id"])
            if doc_id == 6:  # Exclude personal documents for renovations
                continue
            doc_copy = doc.copy()
            if "bullet_points" in doc_copy:
                bullet_points = doc_copy["bullet_points"]
                if isinstance(bullet_points, list):
                    doc_copy["bullet_points"] = bullet_points.copy()
            for field in ("note", "title", "bullet_points"):
                key = (process_type, doc_id, field)
                if key in _RENOVATION_OVERRIDES:
                    doc_copy[field] = _RENOVATION_OVERRIDES[key]
            filtered_docs.append(doc_copy)
        renovation[process_type] = filtered_docs
    return renovation


RENOVATION_DOCUMENT_REQUIREMENTS = _build_renovation_requirements()

ORIENTATION = {
    "title": "Orientações Gerais",
    "rules": [
        "A solicitação será realizada em caráter de excepcionalidade, esgotadas todas as alternativas terapêuticas disponibilizadas pelo SUS",
        "Pacientes residentes no Estado de São Paulo",
        "Tratamento de doença crônica, em caráter ambulatorial",
        "Não será avaliada solicitação de fórmula de manipulação",
        "O médico prescritor deve ser o mesmo em todos os documentos",
        "Documentos em nome do paciente (exceto receita e relatório médico)",
        "Formulários com data inferior a 40 dias",
        "Receitas com data inferior a 30 dias",
    ],
    "note": "A análise do processo leva de 30 a 60 dias após o encaminhamento do processo ao DRS. Você será notificado por email sobre o andamento.",
}

STATUS_LABELS = {
    "rascunho": {
        "label": "Rascunho",
        "color": "gray",
        "description": "Seu processo está em rascunho. Você pode continuar editando e adicionar documentos antes de enviá-lo.",
    },
    "em_revisao": {
        "label": "Em Revisão",
        "color": "blue",
        "description": "Os documentos enviados estão sendo analisados pela nossa equipe. O processo será atualizado em até 24 horas úteis informando pendências ou aprovação para envio ao DRS.",
    },
    "incompleto": {
        "label": "Incompleto",
        "color": "yellow",
        "description": "Encontramos pendências em seu processo.<br><br>Pedimos que corrija os documentos inválidos ou envie os documentos pendentes para que possamos continuar.",
    },
    "completo": {
        "label": "Completo",
        "color": "green",
        "description": "Seu processo está completo e será encaminhado para o DRS-IV de Santos na remessa de [data], onde terá uma segunda avaliação, com posterior envio para Comissão de Farmacologia da Secretaria de Estado da Saúde de São Paulo (SES/SP) para avaliação final.<br><br>O DRS estipula um prazo de 30 a 60 dias a partir do encaminhamento do processo para que haja uma resposta.<br><br>Você será notificado em caso de:<br>• Solicitação de exame/documento pela DRS-IV de Santos<br>• Resposta de deferimento/indeferimento do processo.<br>",
    },
    "enviado": {
        "label": "Enviado",
        "color": "blue",
        "description": "Seu processo foi encaminhado para o DRS-IV de Santos na remessa de [data] e está aguardando análise.<br><br>Você será notificado em caso de:<br>• Solicitação de exame/documento pela DRS-IV de Santos<br>• Resposta de deferimento/indeferimento do processo.<br>",
    },
    "correcao_solicitada": {
        "label": "Correção Solicitada",
        "color": "orange",
        "description": "Seu processo retornou com pendências após análise do DRS-IV de Santos.<br><br>Pedimos que envie os documentos solicitados conforme o retorno do DRS para que possamos dar continuidade ao processo.",
    },
    "autorizado": {
        "label": "Autorizado",
        "color": "green",
        "description": "Seu processo foi autorizado após análise da Comissão de Farmacologia do Estado de São Paulo, e encontra-se em processo de compras.<br><br>A dispensação fica <strong>sob responsabilidade do Estado de São Paulo</strong>, com a retirada sendo feita na <strong>DRS de Santos, localizado no endereço Av. Epitácio Pessoa, 415 - Aparecida, Santos</strong>.<br><br>Para verificar a disponibilidade da retirada, pedimos que entre em contato com o DRS através do número <strong>3278-7767</strong>.",
    },
    "negado": {
        "label": "Negado",
        "color": "red",
        "description": "Seu processo foi negado após análise da Comissão de Farmacologia do Estado de São Paulo.<br><br>A justificativa técnica fornecida pela Comissão se encontra disponível para visualização e download.",
    },
    "expirado": {
        "label": "Expirado",
        "color": "purple",
        "description": "Seu processo expirou após 180 dias da autorização.<br><br>Você pode solicitar a renovação do processo clicando no botão abaixo. A renovação não exige novos documentos pessoais, apenas os documentos médicos atualizados.",
    },
    "outro": {
        "label": "Outro",
        "color": "gray",
        "description": "Status especial do processo.",
    },
}

VALIDATION_STATUS = {
    "pending": {"label": "Pendente", "color": "yellow"},
    "valid": {"label": "Válido", "color": "green"},
    "invalid": {"label": "Inválido", "color": "red"},
}

# Simplified status info for admin templates (label + color only)
# Derived from STATUS_LABELS to ensure consistency
STATUS_INFO = {
    status_key: {"label": info["label"], "color": info["color"]}
    for status_key, info in STATUS_LABELS.items()
}

# Email templates text
EMAIL = {
    "magic_link_subject": "Seu link de acesso - SS-54",
    "magic_link_sent": "Enviamos um link de acesso para seu email. Clique no link para entrar.",
    "magic_link_expires": "O link expira em 15 minutos.",
    "verification_success": "Email verificado com sucesso!",
    "verification_failed": "Link inválido ou expirado. Solicite um novo acesso.",
}

# Error messages
ERRORS = {
    "upload_failed": "Falha ao enviar arquivo. Tente novamente.",
    "invalid_file_type": "Tipo de arquivo não permitido. Use PDF, JPG ou PNG.",
    "file_too_large": "Arquivo muito grande. Tamanho máximo: 10MB.",
    "unauthorized": "Você precisa estar logado para acessar esta página.",
    "process_not_found": "Processo não encontrado.",
}

# Document type ordering and titles for display
DOCUMENT_TYPE_ORDER = [
    "formulario",
    "declaracao",
    "receita",
    "relatorio",
    "documento_pessoal",
    "exame",
    "pdf_combinado",
    "outro",
]

DOCUMENT_TYPE_TITLES = {
    "formulario": "Formulário de Avaliação",
    "declaracao": "Declaração de Conflito de Interesses",
    "receita": "Receita Médica",
    "relatorio": "Relatório Médico",
    "documento_pessoal": "Documentos Pessoais",
    "exame": "Exames Complementares",
    "pdf_combinado": "PDF Combinado",
    "outro": "Outro",
}

# Process type titles (derived from PROCESS_TYPES for convenience)
# Includes "outro" for backward compatibility with existing data
PROCESS_TYPE_TITLES = {key: info["title"] for key, info in PROCESS_TYPES.items()}
PROCESS_TYPE_TITLES["outro"] = "Outro"

# Request type titles
REQUEST_TYPE_TITLES = {
    "primeira_solicitacao": "Primeira Solicitação",
    "renovacao": "Renovação",
}

# Validation status colors and labels (derived from VALIDATION_STATUS)
VALIDATION_COLORS = {k: v["color"] for k, v in VALIDATION_STATUS.items()}
VALIDATION_LABELS = {k: v["label"] for k, v in VALIDATION_STATUS.items()}

# Color classes for Tailwind CSS badges
COLOR_CLASSES = {
    "gray": "bg-gray-100 text-gray-700",
    "blue": "bg-blue-100 text-blue-700",
    "yellow": "bg-yellow-100 text-yellow-700",
    "green": "bg-green-100 text-green-700",
    "red": "bg-red-100 text-red-700",
    "purple": "bg-purple-100 text-purple-700",
    "orange": "bg-orange-100 text-orange-700",
    "slate": "bg-slate-100 text-slate-700",
    "slate800": "bg-slate-100 text-slate-800",
}

# Common labels used across templates
COMMON_LABELS = {
    "not_informed": "Não informado",
    "this_process": "este processo",
    "download": "Baixar",
    "download_model": "Baixar modelo",
    "view_pdf": "Ver PDF",
    "mark_as_sent": "Marcar como Enviado",
    "no_process_found": "Nenhum processo encontrado",
    "try_adjust_filters": "Tente ajustar os filtros de busca",
    "no_documents": "Nenhum documento enviado",
}

# Admin section titles
ADMIN_SECTION_TITLES = {
    "ready_to_send": "Prontos para Envio",
    "sent_to_drs": "Enviados ao DRS",
    "correction_requested": "Correção Solicitada",
    "correction": "Correção",
}

# Email error messages
EMAIL_ERRORS = {
    "status_update_failed": "Status atualizado, mas falhou ao enviar email de notificação ao paciente.",
    "config_error": "Verifique as configurações de SMTP no servidor.",
    "connection_error": "Problema de conexão com servidor de email. Tente novamente.",
    "template_error": "Erro ao gerar conteúdo do email. Contate o suporte técnico.",
    "default_error": "Erro ao enviar mensagem. Tente novamente mais tarde.",
}

# Medication exam requirements
MEDICATION_EXAM_REQUIREMENTS = {
    "medicamentos": {
        "title": "MEDICAMENTOS",
        "categories": [
            {
                "id": "oncologicos",
                "name": "1. Oncológicos (Geral)",
                "requirements": [
                    "Primeira Solicitação: Exame Anatomopatológico (Não há necessidade para Leucemia)"
                ],
            },
            {
                "id": "metilfenidato",
                "name": "2. Metilfenidato / Lisdexanfetamina",
                "requirements": [
                    "Primeira Solicitação: Relatório completo, evolutivo e atualizado da equipe multidisciplinar que acompanha o paciente (Psicólogo, Terapeuta Ocupacional ou Psicopedagogo) dos últimos 6 meses. Pode ser cópia.",
                    "Renovação: Mesmo relatório acima",
                ],
            },
            {
                "id": "hormonais",
                "name": "3. Tamoxifeno / Anastrozol / Exemestano / Letrozol / Fuvestrano",
                "requirements": [
                    "Primeira Solicitação: Exame imunohistoquímico para receptores hormonais, anatomopatológico"
                ],
            },
            {
                "id": "cetuximabe",
                "name": "4. Cetuximabe",
                "requirements": [
                    "Primeira Solicitação: Exame Anatomopatológico; pesquisa de mutações no gene KRAS e NRAS;"
                ],
            },
            {
                "id": "insulinas",
                "name": "5. Insulinas Análogas",
                "requirements": [
                    "Primeira Solicitação: Hemoglobina glicada (Hb1c) e glicemia de jejum (validade até 90 dias). Relatório médico atestando hipoglicemia se houver."
                ],
            },
            {
                "id": "dmri",
                "name": "6. Bevacizumabe (DMRI) / Ranibizumabe",
                "requirements": [
                    "Primeira Solicitação: Mapeamento de retina; Angiografia fluoresceína; OCT - tomografia de coerência óptica (Laudos completos, exames realizados nos últimos 6 meses).",
                    "Renovação: Mesmos exames acima",
                ],
            },
            {
                "id": "teriparatida",
                "name": "7. Teriparatida",
                "requirements": [
                    "Primeira Solicitação: Laudo e Imagens de densitometria óssea (últimos 12 meses); Laudo de radiografias que comprovem fraturas (se houver)"
                ],
            },
            {
                "id": "denosumabe",
                "name": "8. Denosumabe",
                "requirements": [
                    "Primeira Solicitação: Laudo e Imagens de densitometria óssea; Prova de função renal (Albumina, Ureia, Creatinina, Cálcio, Sódio, Potássio, Fósforo); Laudo de radiografias de fraturas, se houver. (Todos exames dos últimos 12 meses).",
                    "Renovação: Laudo e Imagens de densitometria óssea (últimos 12 meses)",
                ],
            },
            {
                "id": "zoledronico",
                "name": "9. Ácido Zoledrônico",
                "requirements": [
                    "Primeira Solicitação: Laudo e Imagens de densitometria óssea (últimos 12 meses); Creatinina, Cálcio, Vitamina D (últimos 6 meses); Laudo de radiografias de fraturas,se houver",
                    "Renovação: Laudo e Imagens de densitometria óssea (últimos 12 meses); Creatinina, Cálcio, Vitamina D (últimos 6 meses)",
                ],
            },
            {
                "id": "omalizumabe",
                "name": "10. Omalizumabe (Urticária)",
                "requirements": [
                    "Primeira Solicitação:",
                    "Exames (últimos 6 meses): hemograma, VHS ou PCR, PPF (3 amostras), IgE, dímero D",
                    "AS7 ou UCT preenchido pelo paciente e vistado pelo médico",
                    "Relatório médico justificando diagnóstico, exclusão de outras urticárias, data de início (mín. 3 meses), anti-histamínicos usados (dose/ordem cronológica)",
                    "Uso atual de anti-histamínicos em 4x a dose da bula por no mínimo 30 dias",
                    "Renovação: Não há renovação (terapia limitada a 9 meses). Repetição requer nova avaliação em Centro de Referência",
                ],
            },
        ],
    },
    "doencas": {
        "title": "DOENÇAS",
        "categories": [
            {
                "id": "puberdade",
                "name": "1. Puberdade Precoce",
                "requirements": [
                    "Primeira Solicitação: Raio-X de idade óssea (últimos 6 meses), LH e FSH (com testes de estímulo, se houver)"
                ],
            },
            {
                "id": "hidradenite",
                "name": "2. Hidradenite e Psoríase",
                "requirements": [
                    "Primeira Solicitação: PPD, sorologia de hepatite B, C e HIV"
                ],
            },
            {
                "id": "prostata",
                "name": "3. Hiperplasia Benigna de Próstata",
                "requirements": [
                    "Primeira Solicitação: Laudo do ultrassom de próstata"
                ],
            },
        ],
    },
}
