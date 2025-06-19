from services.vector_store import vector_store_service
import chromadb

def clear_vector_database():
    """清空向量数据库"""
    print("🗑️ 开始清空向量数据库...")
    
    try:
        # 方法1: 删除所有文档
        print("📊 清空前的统计:")
        stats = vector_store_service.get_collection_stats()
        print(f"   当前文档数: {stats['total_documents']}")
        
        # 获取所有文档ID并删除
        all_data = vector_store_service.collection.get()
        if all_data["ids"]:
            print(f"🗑️ 正在删除 {len(all_data['ids'])} 个文档...")
            vector_store_service.collection.delete(ids=all_data["ids"])
            print("✅ 所有文档已删除")
        else:
            print("ℹ️ 向量数据库已经是空的")
        
        # 验证清空结果
        print("\n📊 清空后的统计:")
        stats_after = vector_store_service.get_collection_stats()
        print(f"   当前文档数: {stats_after['total_documents']}")
        
        if stats_after['total_documents'] == 0:
            print("✅ 向量数据库已完全清空")
        else:
            print("⚠️ 可能还有残留数据")
            
    except Exception as e:
        print(f"❌ 清空向量数据库失败: {e}")
        
        # 方法2: 重置整个collection（如果方法1失败）
        try:
            print("🔄 尝试重置collection...")
            
            # 删除现有collection
            vector_store_service.chroma_client.delete_collection("chat_history")
            print("✅ 旧collection已删除")
            
            # 重新创建collection
            vector_store_service.collection = vector_store_service.chroma_client.create_collection("chat_history")
            print("✅ 新collection已创建")
            
            # 验证
            final_stats = vector_store_service.get_collection_stats()
            print(f"📊 最终统计: {final_stats['total_documents']} 个文档")
            
        except Exception as reset_e:
            print(f"❌ 重置collection也失败: {reset_e}")

if __name__ == "__main__":
    clear_vector_database()