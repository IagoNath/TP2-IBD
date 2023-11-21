import streamlit as st
import sqlite3
import matplotlib.pyplot as plt
import pandas as pd
from pathlib import Path

st.set_option('deprecation.showPyplotGlobalUse', False)

def execute_query(query, cursor):
    cursor.execute(query)
    result = cursor.fetchall()
    return result

def display_query_result(result):
    if not result:
        st.info("No results to display.")
        return

    # Convert the result to a Pandas DataFrame for easy plotting
    df = pd.DataFrame(result, columns=[desc[0] for desc in cursor.description])

    # Display the DataFrame
    st.write(df)

def plot_graph(dataframe, x_column, y_column, num_rows, label_column):
    plt.figure(figsize=(20,10))
    
    bars = plt.barh(dataframe[x_column].head(num_rows), dataframe[y_column].head(num_rows).astype(float))
    plt.xlabel(y_column, fontsize=25)
    plt.ylabel(x_column, fontsize=25)
    plt.xticks(fontsize=20)
    plt.yticks(fontsize=20)
    plt.tight_layout()

    if label_column is not None:
        label_values = label_column.head(num_rows).tolist()
        
        for bar, label in zip(bars, label_values):
            plt.text(bar.get_width(), bar.get_y() + bar.get_height() / 2, str(label),fontsize=20 , ha='left', va='center')

    st.pyplot()


st.title('Contratos.gov.br Contratos')
st.markdown('## Link Banco de Dados')
st.markdown("[Ministério da Gestão e da Inovação em Serviços Públicos: Compras.gov.br Contratos](https://dados.gov.br/dados/conjuntos-dados/comprasgovbr-contratos)")
st.markdown('## Contexto')
st.markdown("O Compras.gov.br Contratos é a plataforma para gestão de contratações públicas que é disponibilizada pelo governo federal e pode ser utilizada por órgãos e entidades da administração pública federal direta, autárquica e fundacional, bem como as empresas estatais; e demais órgãos e entidades de outros poderes ou das esferas estadual e municipal.\
            As consultas a seguir constituem uma análise das relações entre as unidades, orgaos, fornecedores, itens contratados e os tipos e modalidades dos contratos feitos entre 2023-11 e 2023-11-20.")

st.markdown('## Membros')
membros = ["Iago Nathan - 2022043400", "Arthur Rodrigues Diniz - 2022069433", "Lucas Paulo de Oliveira Silva - 2022043469", "Matheus Batista Pederzini de Oliveira - 2021031750"]
for membro in membros:
    st.markdown(f"- {membro}")

st.markdown('## Consultas')

# Load SQL file from the same directory as the app
sql_file_path = Path(__file__).parent / "tp2ibd.sql"

# Check if the SQL file exists
if sql_file_path.exists():
    # Create an in-memory SQLite database connection
    conn = sqlite3.connect(':memory:')
    cursor = conn.cursor()

    # Execute the SQL script from the file
    with open(sql_file_path, 'r') as f:
        sql_script = f.read()
        cursor.executescript(sql_script)
        conn.commit()

    # Define a dictionary with user-friendly names and corresponding SQL queries
    query_mapping = {
        "Query 1: Fornecedores que têm contratos ativos com valores totais acima da \
        média global de valores totais de contratos e que tem média de contratos ativos \
        acima de 70%": 
        {"query": "SELECT fornecedor.fornecedor_nome, CAST(ROUND(AVG(contrato.valor_global), 1) AS TEXT) AS media_valor_total_contratos\
        FROM contrato NATURAL JOIN fornecedor WHERE contrato.situacao = 'Ativo' GROUP BY fornecedor.fornecedor_nome\
        HAVING AVG(contrato.valor_global) > (SELECT AVG(valor_global) FROM contrato) AND fornecedor.fornecedor_nome IN (\
        SELECT fornecedor.fornecedor_nome FROM contrato NATURAL JOIN fornecedor GROUP BY fornecedor.fornecedor_nome\
        HAVING SUM(CASE WHEN contrato.situacao = 'Ativo' THEN 1 ELSE 0 END) * 100.0 / COUNT(contrato.contrato_ID) > 70)\
        ORDER BY CAST(media_valor_total_contratos AS INTEGER) DESC;",
        "have_graph": True},

        "Query 2: Nome das unidades que não possuem contratos\
        com duração abaixo da média das durações de todos os contratos": 
        {"query": "WITH contrato_tempo AS (SELECT contrato_id, unidade_codigo, JULIANDAY(vigencia_fim) - JULIANDAY(vigencia_inicio) AS tempo_contrato\
        FROM contrato ) SELECT u.unidade_nome FROM unidade AS u WHERE u.unidade_codigo NOT IN ( SELECT unidade_codigo FROM\
        contrato_tempo WHERE tempo_contrato < (SELECT AVG(tempo_contrato) FROM contrato_tempo));",
        "have_graph": False},

        "Query 3: Nome dos 5 órgaos com a maior quantidade média de itens por contrado": 
        {"query": "SELECT orgao.orgao_nome, CAST(ROUND(AVG(itemContrato.quantidade),1) AS TEXT) AS quantidade_media_itens\
        FROM orgao NATURAL JOIN contrato NATURAL JOIN itemContrato GROUP BY orgao.orgao_nome ORDER BY\
        CAST(quantidade_media_itens AS INTEGER) DESC LIMIT 5;",
        "have_graph": True},
    
        "Query 4: Nome dos fornecedores com o maior valor total de contratos para cada tipo de contrato": 
        {"query": "WITH contratos_rank AS (SELECT fornecedor_nome, ROUND(SUM(contrato.valor_global), 1) AS total_valor_contratos,\
        tipo_descricao, ROW_NUMBER() OVER (PARTITION BY tipo_descricao ORDER BY SUM(valor_global) DESC) AS RowNum\
        FROM contrato NATURAL JOIN fornecedor NATURAL JOIN tipo GROUP BY fornecedor_nome, tipo_descricao)\
        SELECT fornecedor_nome, CAST(total_valor_contratos AS TEXT) AS total_valor_contratos, tipo_descricao\
        FROM contratos_rank WHERE RowNum = 1 ORDER BY CAST(total_valor_contratos AS INTEGER) DESC;",
        "have_graph": True},

        "Query 5: Porcentagem de contratos de cada tipo e as unidades que contem a maior percentagem de contratos de cada tipo.": 
        {"query": "WITH percentual_contratos_tipo AS (SELECT tipo_descricao, COUNT(contrato_id) AS qtd_contratos,\
        COUNT(contrato_id) * 100.0 / (SELECT COUNT(*) FROM contrato WHERE situacao = 'Ativo') AS percentual_contratos_tipo\
        FROM contrato NATURAL JOIN tipo WHERE situacao = 'Ativo' GROUP BY tipo_descricao), ranked_unidades AS (\
        SELECT tipo_descricao, unidade_nome, COUNT(contrato_id) AS qtd_contratos_unidade,\
        COUNT(contrato_id) * 100.0 / SUM(COUNT(contrato_id)) OVER (PARTITION BY tipo_codigo) AS percentual_contratos_tipo_unidade,\
        ROW_NUMBER() OVER (PARTITION BY tipo_codigo ORDER BY COUNT(contrato_id) DESC) AS rank_unidades\
        FROM contrato NATURAL JOIN unidade NATURAL JOIN tipo WHERE situacao = 'Ativo' GROUP BY tipo_descricao, unidade_nome)\
        SELECT tipo_descricao, percentual_contratos_tipo, unidade_nome AS unidade_maior_qtd_contratos, percentual_contratos_tipo_unidade\
        FROM percentual_contratos_tipo NATURAL JOIN ranked_unidades WHERE rank_unidades = 1 ORDER BY percentual_contratos_tipo DESC;",
        "have_graph": True},

        "Query 6: Nome do fornecedor nome da unidade, data de início da vigência, data de fim da\
        vigência e o valor global de todos os contratos que pertençam a unidades da UFMG.": 
        {"query": "SELECT f.fornecedor_nome, u.unidade_nome, c.vigencia_inicio, c.vigencia_fim, c.valor_global\
        FROM fornecedor AS f JOIN contrato AS c ON f.fornecedor_cnpj_cpf_idgener = c.fornecedor_cnpj_cpf_idgener\
        JOIN unidade AS u ON c.unidade_codigo = u.unidade_codigo WHERE u.unidade_nome_resumido LIKE '%UFMG%';",
        "have_graph": False},

        "Query 7: Obtenha o nome do órgão, o número de contratos, o valor total dos itens e a média do\
        valor do item para cada órgão com mais de cinco contratos ativos e itens acima da média de valor.": 
        {"query": "SELECT o.orgao_nome, COUNT(c.contrato_id) AS numero_contratos, CAST(ROUND(SUM(ic.quantidade * i.item_valor), 1) AS TEXT) AS valor_total,\
        CAST(ROUND(AVG(i.item_valor), 2) AS TEXT) AS media_valor_itens FROM orgao AS o JOIN contrato AS c ON o.orgao_codigo = c.orgao_codigo\
        JOIN itemContrato AS ic ON c.contrato_id = ic.contrato_id JOIN item AS i ON ic.item_id = i.item_id WHERE\
        c.situacao = 'Ativo' AND i.item_valor > (SELECT AVG(item_valor) FROM item) GROUP BY o.orgao_nome HAVING\
        COUNT(DISTINCT c.contrato_id) > 5 ORDER BY CAST (valor_total AS INTEGER) DESC, CAST(media_valor_itens AS INTEGER) DESC",
        "have_graph": True},

        "Query 8: Para cada tipo de contrato seleciona a quantidade, valor total, quantidade de itens e o preço médio de cada item": 
        {"query": "WITH TotalContratoTipo AS (SELECT t.tipo_descricao, COUNT(c.contrato_id) AS qtd_contratos, SUM(c.valor_global) AS total_valor_contratos\
        FROM tipo t JOIN contrato c ON t.tipo_codigo = c.tipo_codigo WHERE c.situacao = 'Ativo' GROUP BY t.tipo_descricao),\
        ItensTipo AS ( SELECT t.tipo_descricao, COUNT(i.quantidade) AS qtd_itens, AVG(i.valortotal) AS media_valor_por_item\
        FROM tipo t JOIN contrato c ON t.tipo_codigo = c.tipo_codigo JOIN itemContrato i ON c.contrato_id = i.contrato_id\
        WHERE c.situacao = 'Ativo' GROUP BY t.tipo_descricao) SELECT tc.tipo_descricao, tc.qtd_contratos, CAST(ROUND(tc.total_valor_contratos, 1) AS TEXT) AS total_valor_contratos,\
        it.qtd_itens, CAST(ROUND(it.media_valor_por_item, 1) AS TEXT) AS media_valor_por_item FROM TotalContratoTipo tc JOIN\
        ItensTipo it ON tc.tipo_descricao = it.tipo_descricao ORDER BY tc.qtd_contratos DESC;",
        "have_graph": False},

        "Query 9: Nome da unidade e o custo total de todos os itens da unidade.": 
        {"query": "SELECT u.unidade_nome, CAST(ROUND(SUM(ic.quantidade * i.item_valor), 1) AS TEXT) AS custo_total FROM\
        item AS i JOIN itemContrato AS ic ON i.item_id = ic.item_id JOIN contrato AS c ON ic.contrato_id = c.contrato_id\
        JOIN unidade AS u ON c.unidade_codigo = u.unidade_codigo WHERE  ic.quantidade > 0 AND i.item_valor > 0 GROUP BY\
        u.unidade_nome ORDER BY CAST(custo_total AS INTEGER) DESC;",
        "have_graph": True},

        "Query 10: Os 20 fornecedores com o maior número de contratos ativos.": 
        {"query": "SELECT f.fornecedor_nome, COUNT(c.fornecedor_cnpj_cpf_idgener) as numero_contratos FROM fornecedor as f\
        JOIN contrato AS c ON f.fornecedor_cnpj_cpf_idgener = c.fornecedor_cnpj_cpf_idgener WHERE c.situacao = 'Ativo'\
        GROUP BY f.fornecedor_nome ORDER BY numero_contratos DESC LIMIT 20;",
        "have_graph": True}
         
        
    }

    query_buttons = list(query_mapping.keys())

    selected_query_name = st.selectbox("Select a Query", query_buttons)

    try:
        selected_query = query_mapping[selected_query_name]
        result = execute_query(selected_query['query'], cursor)
        # Store the result in session state
        st.session_state.current_query_result = result
        st.session_state.current_query_name = selected_query_name

    except Exception as e:
        st.error(f"Error: {e}")
        
    if 'current_query_result' in st.session_state:
        display_query_result(st.session_state.current_query_result)
        if selected_query.get('have_graph', False):
            max_rows = min(20, len(st.session_state.current_query_result) if 'current_query_result' in st.session_state else 20)
            num_rows = st.sidebar.slider("Select the number of rows to display in the graph", 2, max_rows, 2)
            df_result = pd.DataFrame(st.session_state.current_query_result, columns=[desc[0] for desc in cursor.description])
            
            if "Query 10" in selected_query_name:
                x_axis = "fornecedor_nome"
                y_axis = "numero_contratos"
                label = None
            elif "Query 1" in selected_query_name:
                x_axis = "fornecedor_nome"
                y_axis = "media_valor_total_contratos" 
                label = None
            elif "Query 3" in selected_query_name:
                x_axis = "orgao_nome"
                y_axis = "quantidade_media_itens"
                label = None
            elif "Query 4" in selected_query_name:
                x_axis = "fornecedor_nome"
                y_axis = "total_valor_contratos"
                label = df_result["tipo_descricao"].head(num_rows)
            elif "Query 5" in selected_query_name:
                x_axis = "tipo_descricao"
                y_axis = "percentual_contratos_tipo"
                label = df_result["unidade_maior_qtd_contratos"].head(num_rows)
            elif "Query 7" in selected_query_name:
                x_axis = "orgao_nome"
                y_axis = "valor_total"
                label = df_result["numero_contratos"].head(num_rows)
            elif "Query 9" in selected_query_name:
                x_axis = "unidade_nome"
                y_axis = "custo_total"
                label = None
            

            if st.checkbox('Show Graph'):
                plot_graph(pd.DataFrame(st.session_state.current_query_result, columns=[desc[0] for desc in cursor.description]), x_axis, y_axis, num_rows, label)
                
    

else:
    st.error("Failed to find the SQL file.")
