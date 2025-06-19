import asyncpg
from typing import Optional
from config import settings

class CharacterService:
    def __init__(self):
        # 直接使用明确的数据库配置
        self.db_config = {
            "host": "lumilovedb1.chwuqka62eu2.ap-southeast-2.rds.amazonaws.com",
            "port": 5432,
            "database": "Lumilovedb01",
            "user": "postgres",
            "password": "12345678"
        }
        print(f"✅ 角色服务初始化完成")
    
    async def get_character_prompt(self, character_id: str) -> str:
        """从数据库查询角色的prompt_config"""
        try:
            conn = await asyncpg.connect(**self.db_config)
            
            # 查询character表的prompt_config字段
            query = "SELECT name, description, prompt_config FROM character WHERE id = $1"
            result = await conn.fetchrow(query, int(character_id))
            
            await conn.close()
            
            if result:
                name = result["name"]
                description = result["description"] 
                prompt_config = result["prompt_config"]
                
                print(f"✅ 获取角色{character_id}配置成功: {name}")
                
                # 构建完整的角色提示词
                character_prompt = f"""你是{name}。

角色描述：{description}

详细角色设定和规则：
{prompt_config}

请严格按照以上角色设定进行扮演，保持角色的一致性和个性。"""
                
                return character_prompt
            else:
                print(f"❌ 未找到角色{character_id}")
                return "你是一个友好的AI助手。"
                
        except Exception as e:
            print(f"❌ 获取角色配置失败: {e}")
            return "你是一个友好的AI助手。"

# 全局实例
character_service = CharacterService()