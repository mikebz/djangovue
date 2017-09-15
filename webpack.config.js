var path = require("path");
var webpack = require('webpack');
var BundleTracker = require('webpack-bundle-tracker');


module.exports = {
  context: __dirname,

  entry: [
    './frontend/js/main'
  ],
  
  output: {
      path: path.resolve('./frontend/bundles/'),
      filename: "[name]-[hash].js",
  },

  plugins: [
    new webpack.NoEmitOnErrorsPlugin(), 
    new BundleTracker({filename: './webpack-stats.json'}),
  ],

  module: {
    loaders: [
      {
        test: /\.vue$/,
        loader: 'vue-loader',
        options: {
          loaders: {
          }
        }
      },
      {
        test: /\.js$/,
        loader: 'babel-loader',
        exclude: /node_modules/
      },
      {
        test: /\.(png|jpg|gif|svg)$/,
        loader: 'file-loader',
        options: {
          name: '[name].[ext]?[hash]',
          publicPath: 'static/bundles/'
        }
      }
    ],
  },
}
