export const environment = {
  production: true,
  // URL du service Render "shopwise-server" (voir render.yaml). Render dérive le
  // sous-domaine du nom du service tant qu'il est disponible ; si un suffixe a été
  // ajouté (nom déjà pris), remplacer cette valeur par l'URL réelle affichée dans
  // le dashboard Render puis rebuilder le client.
  apiUrl: 'https://shopwise-client.onrender.com',
  firebase: {
    apiKey: "AIzaSyAdl0bt5ww9Dxxr-ozi55hV3abvrbEwwKA",
    authDomain: "shopwise-5f5f1.firebaseapp.com",
    projectId: "shopwise-5f5f1",
    storageBucket: "shopwise-5f5f1.firebasestorage.app",
    messagingSenderId: "60043578055",
    appId: "1:60043578055:web:9276e392833fc822170ce2",
    measurementId: "G-WPVLPQ95FG"
  }
};
