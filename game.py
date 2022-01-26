# encoding=latin-1
import sqlite3
from os import path
from random import randint
from time import time

import pygame
from easygui import enterbox

from font import FontRenderer
from tile import Tile

FOND = pygame.Color(150, 150, 150)

# Merci Microsoft
couleurs_chiffres = {
		1: pygame.Color(0, 0, 255),
		2: pygame.Color(0, 128, 0),
		3: pygame.Color(255, 0, 0),
		4: pygame.Color(0, 0, 128),
		5: pygame.Color(128, 0, 0),
		6: pygame.Color(0, 128, 128),
		7: pygame.Color(0, 0, 0),
		8: pygame.Color(128, 128, 128)
}


class Game:
	def __init__(self, horiz_tiles: int, vert_tiles: int, num_bombs: int = 50):
		assert horiz_tiles > 0
		assert vert_tiles > 0
		pygame.init()
		self.hidden_bombs = 0
		self.num_bombs = num_bombs
		self.flagged = 0
		self.width, self.height = 500, 500
		self.horiz_tiles = horiz_tiles
		self.vert_tiles = vert_tiles
		self.xtilesize = self.width // self.horiz_tiles
		self.ytilesize = self.height // self.vert_tiles
		self.num_tiles = horiz_tiles * vert_tiles

		self.Font = FontRenderer("segoe-ui-symbol.ttf", int(max(self.xtilesize, self.ytilesize) * .6))
		# TODO : meilleures images...
		self.flag_image = pygame.transform.smoothscale(
				pygame.image.load(path.join("resources", "drapeau.png")),
				(self.xtilesize, self.ytilesize))
		self.tile_image = pygame.transform.smoothscale(
				pygame.image.load(path.join("resources", "case.png")),
				(self.xtilesize, self.ytilesize))
		self.bomb_image = pygame.transform.smoothscale(
				pygame.image.load(path.join("resources", "bombe.png")),
				(self.xtilesize, self.ytilesize))

		self.db = sqlite3.connect("records.db")
		# On regarde si la table "records" existe, et sinon on la crée
		if len(self.db.execute(
				"SELECT name FROM sqlite_master WHERE type='table' and name='records';").fetchall()) != 1:
			self.init_db()

		self.running = True
		self.generated = False
		self.lost = False
		self.tiles: list[Tile] = []
		for x in range(self.horiz_tiles):
			for y in range(self.vert_tiles):
				self.tiles.append(Tile(x, y))

		# On modifie ici le nombre de bombes pour pas avoir la fenètre vide pendant ce dialogue
		while self.num_bombs > self.num_tiles - 9:
			self.num_bombs = int(input(
					f"Le nombre de bombes sélectionné est trop grand, merci de le prendre inférieur à {self.num_tiles - 9} :\n"))

		self.screen = pygame.display.set_mode((self.width, self.height), pygame.RESIZABLE)
		self.base_board = self.build_board()

	def init_db(self):
		with self.db:
			self.db.execute("""CREATE TABLE IF NOT EXISTS "records"(
								ID 		INTEGER PRIMARY KEY AUTOINCREMENT,
								NOM 	TEXT   				NOT NULL,
								BOMBES 	INTEGER    			NOT NULL,
								TEMPS 	REAL   				NOT NULL);""")

	def run(self) -> None:
		debut = time()
		temps = 0.
		while self.running:
			# On s'occupe du titre de la fenètre
			if self.lost:
				# TODO : mécanisme pour recommencer une nouvelle partie
				pygame.display.set_caption(
						f"Perdu, il restait {str(self.hidden_bombs)} bombes, temps de jeu : {temps}s")
			else:
				pygame.display.set_caption(
						f"Il reste {str(self.num_bombs - self.flagged)} bombes, temps de jeu : {int(time() - debut)}s")

			# TODO : mécanisme pour recommencer une nouvelle partie
			# Si on a gagné
			if self.generated and self.hidden_bombs == 0:
				self.win(debut)

			# Boucle principale
			for event in pygame.event.get():
				# Quitter le jeu
				if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
					self.running = False

				# Technique secrète pour aller vite
				if event.type == pygame.KEYDOWN:
					if event.key == pygame.K_s and event.mod & pygame.KMOD_CTRL and not self.lost:
						for tile in self.tiles:
							if tile.is_bomb:
								tile.revealed = True

				elif event.type == pygame.KEYUP:
					if event.key == pygame.K_s and not self.lost:
						for tile in self.tiles:
							if tile.is_bomb:
								tile.revealed = False

				# Clic de souris
				if event.type == pygame.MOUSEBUTTONDOWN and not self.lost:
					x, y = event.pos[0] // self.xtilesize, event.pos[1] // self.ytilesize
					clicked_tile = self.tiles[x * self.vert_tiles + y]

					# Clic gauche, on veut révéler une ou des cases
					if event.button == pygame.BUTTON_LEFT:
						# On ne peut pas révéler une case drapeau
						if clicked_tile.flagged: continue
						if not self.generated:
							self.generate(x, y)

						# Si la case est déjà révélée et a autant de drapeaux autour d'elle que de bombes,
						# on peut cliquer dessus pour révéler toutes les cases adjacentes qui n'ont pas de drapeau
						# (si un drapeau a été mal placé, on perd la partie)
						if clicked_tile.revealed:
							num_flagged = sum(neighbour.flagged for neighbour in clicked_tile.neighbours)
							if num_flagged == clicked_tile.bomb_neighbours_count:
								for neighbour in clicked_tile.neighbours:
									if not neighbour.flagged and not neighbour.revealed:
										neighbour.floodfill()
										if neighbour.is_bomb:
											temps = self.lose(debut)

						# On a cliqué sur une bombe cachée
						if clicked_tile.is_bomb:
							temps = self.lose(debut)

						# Sinon on révèle simplement la case cliquée
						else:
							clicked_tile.floodfill()

					# Clic droit, on marque une case d'un drapeau
					elif event.button == pygame.BUTTON_RIGHT and not clicked_tile.revealed:
						# Si la case était déjà marquée, on rajoute la bombe cachée qui avait été enlevée du compte
						if clicked_tile.flagged:
							if clicked_tile.is_bomb:
								self.hidden_bombs += 1
							self.flagged -= 1

						# Sinon, si c'est une bombe on l'enlève du compte des bombes cachées
						else:
							if clicked_tile.is_bomb:
								self.hidden_bombs -= 1
							self.flagged += 1

						# Pour éviter que le titre affiche un compte de bombes restantes négatif
						if self.flagged > self.num_bombs:
							self.flagged = self.num_bombs

						clicked_tile.flagged = not clicked_tile.flagged

				elif event.type == pygame.WINDOWRESIZED:
					self.resize(event)

			# Affichage
			self.display()

	def win(self, debut):
		self.running = False
		temps = time() - debut
		print("GG bg")
		print(f"Temps : {int(temps)}s")
		nom = enterbox("Bien joué, c'est quoi ton petit nom ?", "Entre ton nom")
		nom = nom if nom else "Joueur inconnu"
		self.insere_record(nom, temps)
		self.affiche_records()

	def resize(self, event: pygame.event.Event):
		self.width, self.height = event.x, event.y
		self.xtilesize = self.width // self.horiz_tiles
		self.ytilesize = self.height // self.vert_tiles

		# On redimensionne les images
		self.flag_image = pygame.transform.scale(self.flag_image, (self.xtilesize, self.ytilesize))
		self.bomb_image = pygame.transform.scale(self.bomb_image, (self.xtilesize, self.ytilesize))
		self.tile_image = pygame.transform.scale(self.tile_image, (self.xtilesize, self.ytilesize))

		# On modifie la nouvelle taille de sorte à ne pas avoir de bords noirs autour des cases
		self.width = self.xtilesize * self.horiz_tiles
		self.height = self.ytilesize * self.vert_tiles
		self.screen = pygame.display.set_mode((self.width, self.height), pygame.RESIZABLE)

		self.base_board = self.build_board()

	def display(self) -> None:
		for tile in self.tiles:
			if tile.revealed:
				if tile.is_bomb:
					self.base_board.blit(self.bomb_image,
										 (tile.x * self.xtilesize, tile.y * self.ytilesize))
				else:
					# On affiche le fond et l'éventuel nombre de bombes voisines
					pygame.draw.rect(self.base_board, FOND,
									 pygame.Rect(tile.x * self.xtilesize, tile.y * self.ytilesize,
												 self.xtilesize, self.ytilesize))
					if tile.bomb_neighbours_count > 0:
						text = self.Font.render(str(tile.bomb_neighbours_count),
												couleurs_chiffres[tile.bomb_neighbours_count])
						text_rect = text.get_rect()
						text_rect.center = (tile.x * self.xtilesize + self.xtilesize // 2,
											tile.y * self.ytilesize + self.ytilesize // 2)
						self.base_board.blit(text, text_rect)
			if tile.flagged:
				if not tile.revealed:
					self.base_board.blit(self.tile_image,
										 (tile.x * self.xtilesize, tile.y * self.ytilesize))
				self.base_board.blit(self.flag_image,
									 (tile.x * self.xtilesize, tile.y * self.ytilesize))
			if not (tile.flagged or tile.revealed):
				self.base_board.blit(self.tile_image,
									 (tile.x * self.xtilesize, tile.y * self.ytilesize))
		self.screen.blit(self.base_board, self.base_board.get_rect())
		pygame.display.update()

	def lose(self, debut: float) -> int:
		"""
		Affiche toutes les bombes et termine la partie, et renvoit le temps de jeu.

		:param debut: Le temps de début
		:return: Le temps total de jeu
		"""
		for tile in self.tiles:
			if tile.is_bomb:
				tile.revealed = True
		self.lost = True
		return int(time() - debut)

	def build_board(self) -> pygame.Surface:
		board = pygame.Surface((self.width, self.height))
		for tile in self.tiles:
			if tile.revealed: continue
			board.blit(self.tile_image,
					   (tile.x * self.xtilesize, tile.y * self.ytilesize))
		return board

	def voisins(self, x: int, y: int) -> list[int]:
		"""
		La liste des voisins d'une case sélectionnée. Les voisins sont exprimés en termes d'indices dans le tableau des cases.

		:param x: La coordonnée horizontale.
		:param y: La coordonnée verticale.
		:return: La liste des voisins.
		"""
		v = []
		for i in range(- 1, 2):
			for j in range(- 1, 2):
				if i == j == 0: continue
				if 0 <= x + i < self.horiz_tiles and 0 <= y + j < self.vert_tiles:
					v.append((x + i) * self.vert_tiles + y + j)
		return v

	def generate(self, x: int, y: int) -> None:
		"""
		Génère la liste des bombes et initialise chaque case avec ses voisins.

		:param x: La coordonnée horizontale.
		:param y: La coordonnée verticale.
		"""
		selected_tile_number = x * self.vert_tiles + y
		voisins = self.voisins(x, y)

		# On ajoute toutes les bombes
		while self.hidden_bombs < self.num_bombs:
			i = randint(0, self.num_tiles - 1)

			# On veut que la première case cliquée n'ait aucune bombe parmis ses voisins
			while self.tiles[i].is_bomb or i == selected_tile_number or i in voisins:
				i = randint(0, self.num_tiles - 1)
			self.tiles[i].is_bomb = True
			self.hidden_bombs += 1

		# On calcule la liste des voisins de chaque case
		for i in range(self.num_tiles):
			if i - self.horiz_tiles >= 0:
				self.tiles[i].direct_neighbours.append(self.tiles[i - self.horiz_tiles])
				self.tiles[i].neighbours.append(self.tiles[i - self.horiz_tiles])
				if i % self.vert_tiles > 0:
					self.tiles[i].neighbours.append(self.tiles[i - self.horiz_tiles - 1])
				if i % self.vert_tiles < self.vert_tiles - 1:
					self.tiles[i].neighbours.append(self.tiles[i - self.horiz_tiles + 1])

			if i + self.horiz_tiles < self.num_tiles:
				self.tiles[i].direct_neighbours.append(self.tiles[i + self.horiz_tiles])
				self.tiles[i].neighbours.append(self.tiles[i + self.horiz_tiles])
				if i % self.vert_tiles < self.vert_tiles - 1:
					self.tiles[i].neighbours.append(self.tiles[i + self.horiz_tiles + 1])
				if i % self.vert_tiles > 0:
					self.tiles[i].neighbours.append(self.tiles[i + self.horiz_tiles - 1])

			if i % self.vert_tiles > 0:
				self.tiles[i].direct_neighbours.append(self.tiles[i - 1])
				self.tiles[i].neighbours.append(self.tiles[i - 1])

			if i % self.vert_tiles < self.vert_tiles - 1:
				self.tiles[i].direct_neighbours.append(self.tiles[i + 1])
				self.tiles[i].neighbours.append(self.tiles[i + 1])

		for tile in self.tiles:
			tile.count_neighbour_bombs()

		self.generated = True

	def insere_record(self, nom: str, temps: float):
		with self.db:
			self.db.execute("INSERT INTO 'records' (nom, bombes, temps) VALUES (?, ?, ?)", (nom, self.num_bombs, temps))

	def affiche_records(self):
		with self.db:
			print(f"\nRecords avec {self.num_bombs} bombes :")
			for i, t in enumerate(self.db.execute("SELECT nom, temps from records WHERE BOMBES=(?) ORDER BY TEMPS",
												  (self.num_bombs,)).fetchall()[:5]):
				print(f"\t{i} : {t[0]}, {t[1]:.5}s")
