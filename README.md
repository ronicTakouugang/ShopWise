# 🛍️ ShopWise

ShopWise est une solution intelligente de comparaison de prix multi-plateforme qui permet aux utilisateurs de trouver les meilleures offres en temps réel sur différentes enseignes (Amazon, E.Leclerc, etc.).

L'application combine la puissance du scraping web moderne avec une interface utilisateur fluide pour offrir une expérience d'achat optimisée.

## ✨ Fonctionnalités

- **Recherche Multi-Plateforme** : Comparez instantanément les prix entre plusieurs géants du e-commerce.
- **Scraping en Temps Réel** : Données actualisées directement depuis les sources.
- **Interface Intuitive** : Design moderne et réactif pour une navigation facilitée.
- **Gestion de Compte** : Système d'authentification sécurisé pour une expérience personnalisée.

## 🏗️ Architecture du Projet

Le projet est divisé en deux parties principales :

### 💻 [Client](./client) (Frontend)
- Développé avec **Angular**.
- Interface moderne et responsive.
- Communication fluide avec l'API.

### ⚙️ [Serveur](./server) (Backend)
- Développé avec **Python / Flask**.
- Moteurs de scraping performants (Amazon, Leclerc).
- Base de données pour la gestion des utilisateurs et des préférences.

## 🚀 Démarrage Rapide

### Prérequis
- Node.js & npm (pour le client)
- Python 3.x (pour le serveur)

### Installation

1. **Serveur** :
   ```bash
   cd server
   python -m venv venv
   source venv/bin/activate  # ou venv\Scripts\activate sur Windows
   pip install -r requirements.txt
   python app.py
   ```

2. **Client** :
   ```bash
   cd client
   npm install
   npm start
   ```

Accédez ensuite à l'application via `http://localhost:4200`.

---
*Optimisez vos achats avec ShopWise.*
