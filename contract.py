# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
from genlayer import *
from dataclasses import dataclass
from typing import List

@dataclass
class Meme:
    id: u256
    image_url: str
    description: str
    submitter: Address
    score: u8          # Score sur 100
    votes: u256
    judged_at: str     # Timestamp ou explication

class MemeArena(gl.Contract):
    meme_counter: u256
    memes: TreeMap[u256, Meme]
    top_memes: DynArray[u256, 50]   # IDs des meilleurs memes

    def __init__(self):
        self.meme_counter = 0
        self.memes = TreeMap()
        self.top_memes = DynArray()

    @gl.public.write
    def submit_meme(self, image_url: str, description: str):
        """Soumet un nouveau meme à l'Arena"""
        if len(description) < 5 or len(description) > 280:
            raise gl.vm.UserError("Description doit être entre 5 et 280 caractères")

        self.meme_counter += 1
        meme_id = self.meme_counter

        meme = Meme(
            id=meme_id,
            image_url=image_url,
            description=description,
            submitter=gl.message.sender_address,
            score=0,
            votes=0,
            judged_at=""
        )

        self.memes[meme_id] = meme
        print(f"Nouveau meme soumis #{meme_id} par {gl.message.sender_address}")

        # On juge immédiatement le meme avec l'IA
        self._judge_meme(meme_id)

    def _judge_meme(self, meme_id: u256):
        """Fonction interne qui fait juger le meme par l'IA GenLayer"""
        meme = self.memes[meme_id]

        prompt = f"""
        Tu es un juge expert de memes dans une arène compétitive.
        Évalue ce meme sur 100 points selon les critères suivants :
        - Humour / Originalité
        - Qualité visuelle
        - Pertinence actuelle (culture internet, crypto, GenLayer...)
        - Potentiel viral

        Image URL: {meme.image_url}
        Description: {meme.description}

        Réponds UNIQUEMENT avec un JSON valide :
        {{
            "score": 85,
            "explanation": "Très bon meme, référence claire à GenLayer + humour actuel",
            "strengths": ["original", "pertinent"],
            "weaknesses": ["un peu trop textuel"]
        }}
        """

        # Appel à l'IA via GenLayer (consensus des validators LLM)
        result = gl.llm.generate_structured(
            prompt=prompt,
            schema={
                "type": "object",
                "properties": {
                    "score": {"type": "integer", "minimum": 0, "maximum": 100},
                    "explanation": {"type": "string"},
                    "strengths": {"type": "array"},
                    "weaknesses": {"type": "array"}
                },
                "required": ["score", "explanation"]
            }
        )

        # Mise à jour du score
        meme.score = min(100, max(0, result["score"]))
        meme.judged_at = result["explanation"]
        self.memes[meme_id] = meme

        print(f"Meme #{meme_id} jugé → Score: {meme.score}/100")

    @gl.public.view
    def get_meme(self, meme_id: u256) -> dict:
        meme = self.memes.get(meme_id)
        if not meme:
            return {}
        return {
            "id": meme.id,
            "image_url": meme.image_url,
            "description": meme.description,
            "submitter": str(meme.submitter),
            "score": meme.score,
            "votes": meme.votes,
            "judged_at": meme.judged_at
        }

    @gl.public.view
    def get_top_memes(self, limit: u8 = 12) -> List[dict]:
        """Retourne les meilleurs memes"""
        top = []
        # Tri simple par score (tu peux améliorer avec un meilleur classement)
        all_ids = list(self.memes.keys())
        all_ids.sort(key=lambda x: self.memes[x].score, reverse=True)
        
        for mid in all_ids[:limit]:
            top.append(self.get_meme(mid))
        return top

    @gl.public.write
    def vote_meme(self, meme_id: u256):
        """Vote pour un meme (tu peux ajouter du staking plus tard)"""
        if meme_id not in self.memes:
            raise gl.vm.UserError("Meme introuvable")
        
        meme = self.memes[meme_id]
        meme.votes += 1
        self.memes[meme_id] = meme
