import pygame as pg


class FontRenderer:
	"""
	Une classe simple pour afficher du texte sur une fenètre pygame.
	"""
	def __init__(self, name: str, size: int):
		"""
		Initialise un objet FontRenderer, qui permet d'afficher du texte sur une fenètre pygame.

		:param name: Le nom du fichier de police
		:param size: La taille des lettres
		"""
		self.font = pg.font.SysFont(name, size)
		self.font_name = name
		self.font_size = size

	def render(self, text: str, color: pg.Color) -> pg.Surface:
		return self.font.render(text, True, color)

	def change_font(self, name: str, size: int) -> None:
		self.font = pg.font.Font(name, size)
		self.font_name = name
		self.font_size = size
