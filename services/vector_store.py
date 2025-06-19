import chromadb
from chromadb.config import Settings as ChromaSettings
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from typing import List, Dict, Any
import uuid
from config import settings

class VectorStoreService:
    def __init__(self):
        # 使用标准的HuggingFace embedding模型
        self.embeddings = HuggingFaceEmbeddings(
            model_name=settings.embedding_model,  # "sentence-transformers/all-MiniLM-L6-v2"
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': False}
        )
        
        print(f"✅ 使用HuggingFace embedding模型: {settings.embedding_model}")
        
        # 初始化ChromaDB
        self.chroma_client = chromadb.PersistentClient(
            path=settings.chroma_persist_directory,
            settings=ChromaSettings(allow_reset=True)
        )
        
        # 创建collection
        self.collection_name = "chat_history"
        try:
            self.collection = self.chroma_client.get_collection(self.collection_name)
        except:
            self.collection = self.chroma_client.create_collection(self.collection_name)
        
        # 初始化LangChain向量存储
        self.vector_store = Chroma(
            client=self.chroma_client,
            collection_name=self.collection_name,
            embedding_function=self.embeddings
        )
        
        # 文本分割器
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
        )
        
        print("✅ 向量存储服务初始化完成")
    
    def add_chat_to_vector_store(self, user_id: str, session_id: str, 
                                conversation_context: List[Dict[str, str]]):
        """将聊天对话添加到向量数据库"""
        documents = []
        metadatas = []
        
        for i, msg in enumerate(conversation_context):
            # 创建文档内容
            doc_content = f"用户: {msg.get('user', '')}\n助手: {msg.get('assistant', '')}"
            
            # 分割长文本
            chunks = self.text_splitter.split_text(doc_content)
            
            for chunk in chunks:
                documents.append(chunk)
                metadatas.append({
                    "user_id": user_id,
                    "session_id": session_id,
                    "message_index": i,
                    "type": "conversation",
                    "chunk_id": str(uuid.uuid4())
                })
        
        if documents:
            # 生成唯一ID
            ids = [str(uuid.uuid4()) for _ in documents]
            
            try:
                # 添加到向量数据库
                self.vector_store.add_texts(
                    texts=documents,
                    metadatas=metadatas,
                    ids=ids
                )
                print(f"✅ 已添加{len(documents)}个文档到向量数据库")
            except Exception as e:
                print(f"❌ 添加向量数据失败: {e}")
    
    def search_relevant_context(self, query: str, user_id: str, 
                               session_id: str = None, k: int = None) -> List[Dict]:
        """搜索相关的上下文"""
        if k is None:
            k = settings.top_k_results
        
        print(f"🔍 向量搜索参数: query='{query}', user_id='{user_id}', session_id='{session_id}', k={k}")
        
        # 构建过滤条件
        if session_id:
            filter_dict = {
                "$and": [
                    {"user_id": user_id},
                    {"session_id": session_id}
                ]
            }
        else:
            filter_dict = {"user_id": user_id}
        
        print(f"🔍 使用过滤条件: {filter_dict}")
        
        try:
            # 执行相似度搜索
            results = self.vector_store.similarity_search_with_score(
                query=query,
                k=k,
                filter=filter_dict
            )
            
            # 格式化结果
            context_results = []
            for doc, score in results:
                # 验证结果确实匹配过滤条件
                doc_user_id = doc.metadata.get('user_id')
                doc_session_id = doc.metadata.get('session_id')
                
                if str(doc_user_id) == str(user_id) and str(doc_session_id) == str(session_id):
                    context_results.append({
                        "content": doc.page_content,
                        "metadata": doc.metadata,
                        "similarity_score": score
                    })
                else:
                    print(f"⚠️ 警告: 过滤器未正确工作，文档元数据不匹配")
                    print(f"   期望: user_id='{user_id}', session_id='{session_id}'")
                    print(f"   实际: user_id='{doc_user_id}', session_id='{doc_session_id}'")
            
            print(f"✅ 找到{len(context_results)}个相关上下文")
            return context_results
            
        except Exception as e:
            print(f"❌ 向量搜索失败: {e}")
            return []
    
    def delete_session_vectors(self, session_id: str):
        """删除特定会话的向量数据"""
        try:
            # 获取该会话的所有文档ID
            results = self.collection.get(
                where={"session_id": session_id}
            )
            
            if results["ids"]:
                self.collection.delete(ids=results["ids"])
                print(f"✅ 已删除会话 {session_id} 的向量数据")
        except Exception as e:
            print(f"❌ 删除会话向量失败: {e}")
    
    def get_collection_stats(self):
        """获取向量数据库统计信息"""
        try:
            count = self.collection.count()
            return {
                "total_documents": count,
                "collection_name": self.collection_name
            }
        except Exception as e:
            print(f"❌ 获取统计信息失败: {e}")
            return {
                "total_documents": 0,
                "collection_name": self.collection_name
            }

# 全局向量存储服务实例
vector_store_service = VectorStoreService()
