class Tile:
	"""
	Une classe simple permettant de stocker une case et ses attributs.
	"""

	def __init__(self, x: int, y: int):
		"""
		Initialise une case aux coordonn�es donn�es.

		:param x: La coordonn�e horizontale
		:param y: La coordonn�e verticale
		"""
		self.x, self.y = x, y
		self.neighbours: list[Tile] = []
		self.direct_neighbours: list[Tile] = []
		self.is_bomb = False
		self.revealed = False
		self.flagged = False
		self.bomb_neighbours_count = 0
		self.count_neighbour_bombs()

	def count_neighbour_bombs(self) -> None:
		"""
		Compte le nombre de bombes voisines, et le stocke pour utilisation future
		"""
		self.bomb_neighbours_count = sum(neighbour.is_bomb for neighbour in self.neighbours)

	def floodfill(self) -> None:
		"""
		R�v�le cette case et appelle cette m�thode sur les cases voisines.
		"""
		self.revealed = True
		if self.is_bomb or self.bomb_neighbours_count != 0: return
		for neighbour in self.neighbours:
			if not neighbour.revealed and not neighbour.is_bomb:
				neighbour.floodfill()
