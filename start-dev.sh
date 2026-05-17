#!/bin/bash
# start-dev.sh - Script pour démarrer l'environnement de développement complet

echo "🚀 Démarrage de JobMatch..."
echo ""

# Vérifier que nous sommes dans le bon répertoire
if [ ! -f "backend/app.py" ]; then
    echo "❌ Erreur: Exécutez ce script depuis la racine du projet"
    exit 1
fi

# Démarrer le backend
echo "📡 Démarrage du backend (port 5000)..."
cd backend
.\.venv\Scripts\python.exe app.py &
BACKEND_PID=$!
sleep 2

# Démarrer le frontend
echo "🖥️ Démarrage du frontend (port 8080)..."
cd ../frontend
python -m http.server 8080 &
FRONTEND_PID=$!
sleep 1

echo ""
echo "✅ JobMatch est prêt!"
echo ""
echo "📍 Accès :"
echo "  - Frontend  : http://localhost:8080"
echo "  - Backend   : http://localhost:5000"
echo "  - API Docs  : http://localhost:5000"
echo ""
echo "⏹️  Pour arrêter, appuyez sur Ctrl+C"
echo ""

# Attendre Ctrl+C
wait
