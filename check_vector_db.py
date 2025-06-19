from services.vector_store import vector_store_service
import asyncio

def check_vector_database():
    """检查向量数据库状态"""
    print("🔍 检查向量数据库状态...")
    
    # 1. 获取统计信息
    stats = vector_store_service.get_collection_stats()
    print(f"📊 向量数据库统计: {stats}")
    
    # 2. 获取所有数据（最多10条）
    try:
        all_data = vector_store_service.collection.get(limit=10)
        print(f"\n📋 数据库中的文档:")
        print(f"   总文档数: {len(all_data['documents'])}")
        
        for i, (doc, metadata) in enumerate(zip(all_data['documents'], all_data['metadatas'])):
            print(f"\n  文档 {i+1}:")
            print(f"    内容: {doc[:100]}...")
            print(f"    元数据: {metadata}")
            
    except Exception as e:
        print(f"❌ 获取文档失败: {e}")
    
    # 3. 测试搜索功能
    test_queries = ["what's my name", "thomas", "name"]
    
    for query in test_queries:
        print(f"\n🔍 测试搜索: '{query}'")
        results = vector_store_service.search_relevant_context(
            query=query,
            user_id="1",
            session_id="user_1_character_2",
            k=3
        )
        
        print(f"   结果数量: {len(results)}")
        for i, result in enumerate(results):
            print(f"   结果{i+1}: 相似度={result.get('similarity_score', 0):.3f}")
            print(f"          内容: {result['content'][:100]}...")

if __name__ == "__main__":
    check_vector_database()